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

