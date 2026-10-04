from django.db import models
from django.db.models import Q

from apps.core.models import Photo


class Category(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Colour(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=60)
    hex = models.CharField(max_length=7, help_text="Swatch colour, for example #c8b59a.")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Size(models.Model):
    """A size in one of the size systems: letters for clothes, EU numbers for shoes, one size."""

    class System(models.TextChoices):
        LETTER = "letter", "Letters (XS to XL)"
        SHOE = "shoe", "Shoes (EU)"
        ONE = "one", "One size"

    code = models.SlugField(unique=True)
    label = models.CharField(max_length=20)
    system = models.CharField(max_length=10, choices=System.choices)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["system", "position"]

    def __str__(self):
        return self.label


class Product(models.Model):
    class Department(models.TextChoices):
        WOMEN = "women", "Women"
        MEN = "men", "Men"
        UNISEX = "unisex", "Unisex"

    class Status(models.TextChoices):
        ACTIVE = "active", "On sale"
        DRAFT = "draft", "Draft"
        ARCHIVED = "archived", "Archived"

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=160)
    department = models.CharField(max_length=10, choices=Department.choices, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    description = models.TextField(blank=True)
    details = models.JSONField(default=list, blank=True, help_text="Short bullet points: fit, closures, pockets.")
    composition = models.CharField(max_length=200, blank=True)
    care = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    compare_at_price = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, help_text="The old price, when the product is on sale."
    )
    is_new = models.BooleanField(default=False)
    popularity = models.PositiveIntegerField(default=0, help_text="Higher comes first in the default sort.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-popularity", "name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(compare_at_price__isnull=True) | Q(compare_at_price__gt=models.F("price")),
                name="compare_at_price_above_price",
            )
        ]

    def __str__(self):
        return self.name

    @property
    def on_sale(self) -> bool:
        return self.compare_at_price is not None


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    photo = models.ForeignKey(Photo, on_delete=models.PROTECT, related_name="+")
    colour = models.ForeignKey(
        Colour, on_delete=models.SET_NULL, null=True, blank=True, help_text="The colour shown, if the photo is of one."
    )
    alt = models.CharField(max_length=200)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.product} #{self.position}"


class Variant(models.Model):
    """One colour in one size: the thing that is actually stocked and sold."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    colour = models.ForeignKey(Colour, on_delete=models.PROTECT)
    size = models.ForeignKey(Size, on_delete=models.PROTECT)
    sku = models.CharField(max_length=40, unique=True)
    stock = models.IntegerField(default=0)

    class Meta:
        ordering = ["product", "colour__name", "size__position"]
        constraints = [
            models.UniqueConstraint(fields=["product", "colour", "size"], name="unique_variant"),
            # The last line of defence against overselling: see orders.services.reserve
            models.CheckConstraint(condition=Q(stock__gte=0), name="stock_not_negative"),
        ]

    def __str__(self):
        return f"{self.product} / {self.colour} / {self.size}"


class Collection(models.Model):
    """A curated edit, shown as an editorial page."""

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=120)
    subtitle = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    photo = models.ForeignKey(Photo, on_delete=models.PROTECT, related_name="+")
    alt = models.CharField(max_length=200)
    position = models.PositiveSmallIntegerField(default=0)
    products = models.ManyToManyField(Product, related_name="collections", blank=True)

    class Meta:
        ordering = ["position", "title"]

    def __str__(self):
        return self.title
