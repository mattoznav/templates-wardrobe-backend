from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Editorial, Store


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        exclude = ["id"]


@api_view(["GET"])
@permission_classes([AllowAny])
def store(request):
    return Response(StoreSerializer(Store.objects.first()).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def editorial(request):
    """Copy and images for the pages around the catalogue, keyed by place (for example `home-hero`)."""
    return Response(
        {
            e.key: {
                "title": e.title,
                "text": e.text,
                "alt": e.alt,
                "image": {
                    "url": e.photo.url,
                    "photographer": e.photo.photographer,
                    "photographer_url": e.photo.photographer_url,
                    "source_url": e.photo.source_url,
                },
            }
            for e in Editorial.objects.select_related("photo")
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})
