from django.conf import settings
from django.db import transaction
from django.db.models import Count, F, Prefetch, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.models import Photo
from apps.core.permissions import IsStaff, IsStaffOrReadOnly
from apps.orders.services import release_expired

from .models import Category, Collection, Colour, Product, ProductImage, Size, Variant


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["slug", "name", "position"]


class ColourSerializer(serializers.ModelSerializer):
    class Meta:
        model = Colour
        fields = ["slug", "name", "hex"]


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ["code", "label", "system", "position"]


def photo_fields(photo: Photo) -> dict:
    return {
        "url": photo.url,
        "photographer": photo.photographer,
        "photographer_url": photo.photographer_url,
        "source_url": photo.source_url,
    }


class ImageSerializer(serializers.ModelSerializer):
    """Read: the photo with its credit. Write: the same fields, the photo is created if new."""

    url = serializers.URLField(max_length=300)
    photographer = serializers.CharField(max_length=120)
    photographer_url = serializers.URLField(max_length=300)
    source_url = serializers.URLField(max_length=300)
    colour = serializers.SlugRelatedField(slug_field="slug", queryset=Colour.objects.all(), allow_null=True, required=False)

    class Meta:
        model = ProductImage
        fields = ["url", "alt", "colour", "photographer", "photographer_url", "source_url"]

    def to_representation(self, image):
        return {"alt": image.alt, "colour": image.colour.slug if image.colour else None, **photo_fields(image.photo)}


class VariantSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    colour = serializers.SlugRelatedField(slug_field="slug", queryset=Colour.objects.all())
    size = serializers.SlugRelatedField(slug_field="code", queryset=Size.objects.all())
    sku = serializers.CharField(max_length=40, required=False, allow_blank=True)
    stock = serializers.IntegerField(min_value=0)

    class Meta:
        model = Variant
        fields = ["id", "sku", "colour", "size", "stock"]


def _ordered_unique(items, key):
    seen, out = set(), []
    for item in items:
        if key(item) not in seen:
            seen.add(key(item))
            out.append(item)
    return out


class ProductSerializer(serializers.ModelSerializer):
    """Everything a product page needs. Staff can write images and variants in the same request."""

    category = serializers.SlugRelatedField(slug_field="slug", queryset=Category.objects.all())
    category_name = serializers.CharField(source="category.name", read_only=True)
    images = ImageSerializer(many=True, required=False)
    variants = VariantSerializer(many=True, required=False)
    colours = serializers.SerializerMethodField()
    sizes = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    on_sale = serializers.BooleanField(read_only=True)
    collections = serializers.SlugRelatedField(slug_field="slug", many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "slug", "name", "department", "category", "category_name", "status", "description", "details",
            "composition", "care", "price", "compare_at_price", "on_sale", "is_new", "popularity", "colours", "sizes",
            "in_stock", "images", "variants", "collections", "created_at",
        ]
        read_only_fields = ["created_at"]

    def get_colours(self, product):
        # In the order the variants were created: the first is the colour photographed first
        variants = sorted(product.variants.all(), key=lambda v: v.id)
        return [ColourSerializer(c).data for c in _ordered_unique([v.colour for v in variants], lambda c: c.id)]

    def get_sizes(self, product):
        sizes = sorted(_ordered_unique([v.size for v in product.variants.all()], lambda s: s.id), key=lambda s: s.position)
        return [{"code": s.code, "label": s.label} for s in sizes]

    def get_in_stock(self, product):
        return any(v.stock > 0 for v in product.variants.all())

    def validate(self, attrs):
        price = attrs.get("price", getattr(self.instance, "price", None))
        compare = attrs.get("compare_at_price", getattr(self.instance, "compare_at_price", None))
        if compare is not None and price is not None and compare <= price:
            raise ValidationError({"compare_at_price": "The old price must be higher than the price."})
        variants = attrs.get("variants")
        if variants is not None:
            combos = [(v["colour"].id, v["size"].id) for v in variants]
            if len(set(combos)) != len(combos):
                raise ValidationError({"variants": "Each colour and size pair can only appear once."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        images = validated_data.pop("images", [])
        variants = validated_data.pop("variants", [])
        product = Product.objects.create(**validated_data)
        self._save_images(product, images)
        self._save_variants(product, variants)
        return product

    @transaction.atomic
    def update(self, product, validated_data):
        images = validated_data.pop("images", None)
        variants = validated_data.pop("variants", None)
        product = super().update(product, validated_data)
        if images is not None:
            product.images.all().delete()
            self._save_images(product, images)
        if variants is not None:
            self._save_variants(product, variants)
        return product

    def _save_images(self, product, images):
        for position, data in enumerate(images):
            photo, _ = Photo.objects.update_or_create(
                url=data["url"],
                defaults={k: data[k] for k in ("photographer", "photographer_url", "source_url")},
            )
            ProductImage.objects.create(
                product=product, photo=photo, colour=data.get("colour"), alt=data.get("alt") or product.name, position=position
            )

    def _save_variants(self, product, variants):
        """Upsert by id; variants left out are removed unless they were ever ordered."""
        keep = []
        for data in variants:
            existing = product.variants.filter(pk=data.get("id")).first() if data.get("id") else None
            sku = data.get("sku") or f"{product.slug}-{data['colour'].slug}-{data['size'].code}".upper()[:40]
            if existing:
                existing.colour, existing.size, existing.stock = data["colour"], data["size"], data["stock"]
                existing.sku = sku
                existing.save()
                keep.append(existing.pk)
            else:
                keep.append(Variant.objects.create(product=product, colour=data["colour"], size=data["size"], sku=sku, stock=data["stock"]).pk)
        removed = product.variants.exclude(pk__in=keep)
        if removed.filter(order_lines__isnull=False).exists():
            raise ValidationError({"variants": "Variants that were ordered cannot be removed. Set their stock to 0 instead."})
        removed.delete()


def product_queryset():
    return Product.objects.select_related("category").prefetch_related(
        Prefetch("images", queryset=ProductImage.objects.select_related("photo", "colour")),
        Prefetch("variants", queryset=Variant.objects.select_related("colour", "size").order_by("size__position", "colour__name")),
        "collections",
    )


SORTS = {
    "featured": ["-popularity", "name"],
    "newest": ["-is_new", "-created_at", "-popularity"],
    "price_asc": ["price", "name"],
    "price_desc": ["-price", "name"],
}


def split(value: str | None) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()] if value else []


class ProductViewSet(viewsets.ModelViewSet):
    """Products. Filters (comma lists allowed): `department`, `category`, `colour`, `size`, `collection`,
    `q`, `on_sale=1`, `new=1`, `in_stock=1`, `sort` (featured, newest, price_asc, price_desc).
    Staff also see drafts and archived products and can filter by `status`."""

    serializer_class = ProductSerializer
    permission_classes = [IsStaffOrReadOnly]
    lookup_field = "slug"
    pagination_class = None

    def get_queryset(self):
        qs = product_queryset()
        params = self.request.query_params
        if not self.request.user.is_staff:
            qs = qs.filter(status=Product.Status.ACTIVE)
        elif statuses := split(params.get("status")):
            qs = qs.filter(status__in=statuses)
        if departments := split(params.get("department")):
            qs = qs.filter(department__in=departments)
        if categories := split(params.get("category")):
            qs = qs.filter(category__slug__in=categories)
        if colours := split(params.get("colour")):
            qs = qs.filter(variants__colour__slug__in=colours)
        if sizes := split(params.get("size")):
            qs = qs.filter(variants__size__code__in=sizes, variants__stock__gt=0)
        if collection := params.get("collection"):
            qs = qs.filter(collections__slug=collection)
        if q := params.get("q", "").strip():
            qs = qs.filter(Q(name__icontains=q) | Q(category__name__icontains=q) | Q(variants__sku__iexact=q))
        if params.get("on_sale") == "1":
            qs = qs.filter(compare_at_price__isnull=False)
        if params.get("new") == "1":
            qs = qs.filter(is_new=True)
        if params.get("in_stock") == "1":
            qs = qs.filter(variants__stock__gt=0)
        return qs.distinct().order_by(*SORTS.get(params.get("sort", ""), SORTS["featured"]))

    def list(self, request, *args, **kwargs):
        release_expired()
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        release_expired()
        return super().retrieve(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        if Variant.objects.filter(product=product, order_lines__isnull=False).exists():
            return Response(
                {"detail": "This product has been ordered. Archive it instead of deleting it."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)


class InventorySerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField()
    colour = ColourSerializer(read_only=True)
    size = serializers.CharField(source="size.label", read_only=True)

    class Meta:
        model = Variant
        fields = ["id", "sku", "product", "colour", "size", "stock"]

    def get_product(self, v):
        images = list(v.product.images.all())
        image = next((i for i in images if i.colour_id == v.colour_id), images[0] if images else None)
        return {"slug": v.product.slug, "name": v.product.name, "status": v.product.status, "image": image.photo.url if image else ""}


class StockAdjustSerializer(serializers.Serializer):
    delta = serializers.IntegerField()


class InventoryViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Staff: every variant with its stock. Filters: `q` (product or SKU), `low=1`, `category`."""

    serializer_class = InventorySerializer
    permission_classes = [IsStaff]

    def get_queryset(self):
        qs = Variant.objects.select_related("product", "colour", "size").prefetch_related(
            Prefetch("product__images", queryset=ProductImage.objects.select_related("photo"))
        )
        params = self.request.query_params
        if q := params.get("q", "").strip():
            qs = qs.filter(Q(product__name__icontains=q) | Q(sku__icontains=q))
        if params.get("low") == "1":
            qs = qs.filter(stock__lte=settings.LOW_STOCK_THRESHOLD)
        if category := params.get("category"):
            qs = qs.filter(product__category__slug=category)
        return qs.order_by("stock", "product__name", "size__position") if params.get("low") == "1" else qs.order_by("product__name", "colour__name", "size__position")

    @action(detail=True, methods=["post"])
    def adjust(self, request, pk=None):
        """Add or remove pieces, for deliveries and stock counts. Safe while orders come in."""
        data = StockAdjustSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        delta = data.validated_data["delta"]
        updated = Variant.objects.filter(pk=pk, stock__gte=-delta).update(stock=F("stock") + delta)
        if not updated:
            if not Variant.objects.filter(pk=pk).exists():
                return Response(status=status.HTTP_404_NOT_FOUND)
            return Response({"detail": "Stock cannot go below zero."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(InventorySerializer(self.get_queryset().get(pk=pk)).data)


class CollectionSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Collection
        fields = ["slug", "title", "subtitle", "description", "image", "alt", "product_count"]

    def get_image(self, collection):
        return photo_fields(collection.photo)


class CollectionViewSet(viewsets.ReadOnlyModelViewSet):
    """Curated edits. The products are at `/api/products/?collection=<slug>`."""

    serializer_class = CollectionSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    lookup_field = "slug"

    def get_queryset(self):
        return Collection.objects.select_related("photo").annotate(
            product_count=Count("products", filter=Q(products__status=Product.Status.ACTIVE))
        )


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None
    lookup_field = "slug"
    queryset = Category.objects.all()


class ColourViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ColourSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    lookup_field = "slug"
    queryset = Colour.objects.all()


class SizeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SizeSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    lookup_field = "code"
    queryset = Size.objects.all()


def stock_totals():
    """Pieces in stock and number of variants running low, for the dashboard."""
    return Variant.objects.filter(product__status=Product.Status.ACTIVE).aggregate(
        pieces=Coalesce(Sum("stock"), 0), low=Count("id", filter=Q(stock__lte=settings.LOW_STOCK_THRESHOLD))
    )
