# Demo data

Each CSV file is a database table. `id` is the primary key, `<table>_id` columns are foreign keys, and list fields (product details) are separated by `|`.

All files are written by [`tools/build_catalog.py`](../tools/build_catalog.py). Edit the script and run it again, or edit the files by hand; then reload with `python manage.py load_data`.

## Sources

- Photos (`photos.csv`): from [Unsplash](https://unsplash.com), under the [Unsplash License](https://unsplash.com/license). Each row keeps the photographer, their profile and the source page. The images are loaded from the Unsplash CDN, not stored here.
- Everything else (the store, products, descriptions, prices, colours, sizes, stock, collections, shipping) is fictional.
