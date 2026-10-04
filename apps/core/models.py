from django.db import models


class Store(models.Model):
    """The shop itself. The template runs a single brand with one physical store."""

    name = models.CharField(max_length=120)
    tagline = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=2)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    opening_hours = models.CharField(max_length=200, blank=True)
    timezone = models.CharField(max_length=60)
    currency = models.CharField(max_length=3)
    free_shipping_over = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    return_window_days = models.PositiveSmallIntegerField(default=30)

    def __str__(self):
        return self.name


class Photo(models.Model):
    """Credit for a photograph. Every image shown by the shop points to one."""

    url = models.URLField(max_length=300, unique=True)
    photographer = models.CharField(max_length=120)
    photographer_url = models.URLField(max_length=300)
    source_url = models.URLField(max_length=300, help_text="The page of the photo, for attribution.")

    def __str__(self):
        return self.url


class Editorial(models.Model):
    """Images and copy for the pages around the catalogue: home hero, departments, story blocks."""

    key = models.SlugField(unique=True)
    title = models.CharField(max_length=160, blank=True)
    text = models.TextField(blank=True)
    photo = models.ForeignKey(Photo, on_delete=models.PROTECT, related_name="+")
    alt = models.CharField(max_length=200)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key
