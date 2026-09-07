unicorn.github.io
=================

Static site for dozingunicorn

Tools
-----

### sync-images.py

requires `.b2env` file with auth secrets

```dotenv
## Required blocks
B2_BUCKET = b2://my-b2-bucket/path
B2_APPLICATION_KEY_ID = 
B2_APPLICATION_KEY = \\SECRET\\

## Helpful blocks
# b2://my-b2-bucket/path/{{ LATEST_PATH }}
# Article paths should always point to `latest`
LATEST_PATH = latest

# Local logging path
LOGGING_PATH = /tmp/unicorn/sync-images

```

### Various Helpers

#### Disable .DS_Store on `_images` path

Though ignore patterns have been added to tools, releasing `.DS_Store` files to a public S3 is not preferred

```bash
sudo cp -af /dev/null _images/.DS_Store && sudo chmod a=rw _images/.DS_Store
```