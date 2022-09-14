import glob
import os.path

song_dir = ""

bad_txt_names = ["notes", "instrumental", "duet-instrumental", "duet", "file"]


def main():
    for bad_name in bad_txt_names:
        bad_named_files = glob.glob(f"{glob.escape(song_dir)}/**/{glob.escape(bad_name)}.[Tt][Xx][Tt]", recursive=True)
        for bad_file in bad_named_files:
            directory = os.path.dirname(bad_file)
            directory_name = os.path.basename(directory)
            new_name = f"{directory_name} ({bad_name.capitalize()}).txt"
            print(f"{bad_file}  =>  {new_name}")
            os.rename(bad_file, os.path.join(directory, new_name))


if __name__ == '__main__':
    main()
