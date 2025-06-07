from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
import os

class PhotoGrouper:
    def __init__(self, image_paths, threshold_seconds=0.5):
        self.image_paths = image_paths
        self.threshold = threshold_seconds
        self.groups = self._group_images()

    def _get_image_timestamp(self, path):
        try:
            img = Image.open(path)
            exif = img._getexif()
            if exif:
                for tag, value in exif.items():
                    if TAGS.get(tag) == "DateTimeOriginal":
                        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S").timestamp()
        except:
            pass
        try:
            return os.path.getmtime(path)
        except:
            return None

    def _group_images(self):
        groups = []
        current_group = []
        prev_time = None

        timestamped_images = []
        for path in self.image_paths:
            ts = self._get_image_timestamp(path)
            if ts is not None:
                timestamped_images.append((ts, path))

        timestamped_images.sort()

        for mtime, path in timestamped_images:
            if not prev_time or (mtime - prev_time <= self.threshold):
                current_group.append(path)
            else:
                groups.append(current_group)
                current_group = [path]

            prev_time = mtime

        if current_group:
            groups.append(current_group)

        return groups