from flask import current_app
def allowfilename(filename: str) -> bool: 
    ALLOWED_PICTURE_EXTENSIONS:set[str] = current_app.config.get('ALLOWED_PICTURE_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif'})

    if "." not in filename:
        return False
    ext = filename.split(".")[-1]
    if ext.lower() not in ALLOWED_PICTURE_EXTENSIONS:
        return False
    return True