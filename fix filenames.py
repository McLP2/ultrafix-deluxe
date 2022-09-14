import os
import re
import string
import sys

song_dir = ""

allowed_chars = string.printable + "ÄÖÜäöüëßÁÉÍÓÚáéíóúÀÈÌÒÙàèìòùÂÊÎÔÛâêîôûÇçĘęĄąÃãÑñÅåæ"

fixes = {"Ã¼": "ü",
         "": "ä",
         "": "Ä",
         "´": "'",
         "": "ö",
         "ü": "ü",
         "": "é",
         "": "ü",
         "": "x",
         "é": "é",
         "Ä": "Ä",
         # "á": "ß",  # á can be valid
         # "ï": "'",  # ï can be valid
         "’": "'",
         "ä": "ä",
         "–": "-",
         "": "ę",
         "": "ù",
         " ": "á",
         "ö": "ö",
         "¿": "",
         "¨": "",
         "¢": "ó",
         "£": "ú",
         "": "æ",
         "": "'s",
         "": "è",
         "¦": "'"}


def is_good(file_name):
    result, _ = re.subn(f"[{re.escape(allowed_chars)}]", '', file_name)
    return len(result) == 0


def fix(file_name):
    for bad, good in fixes.items():
        file_name = file_name.replace(bad, good)
    return file_name


def check_filename(file_name):
    if is_good(file_name):
        return file_name
    new_name = fix(file_name)
    # print(f"{file_name}  =>  {new_name}")
    if not is_good(new_name):
        print(new_name, file=sys.stderr, flush=True)
        exit()
    return new_name


def traverse(root):
    directory = os.listdir(root)
    for content in directory:
        new_name = check_filename(content)
        old_full_path = os.path.join(root, content)
        new_full_path = os.path.join(root, new_name)
        if new_name != content:
            if os.path.exists(new_full_path):
                print(f"Already exists: {new_name}", file=sys.stderr, flush=True)
            else:
                os.rename(old_full_path, new_full_path)
        if os.path.isdir(new_full_path):
            traverse(new_full_path)


def main():
    traverse(song_dir)


if __name__ == '__main__':
    main()
