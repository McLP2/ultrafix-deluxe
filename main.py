import os
import glob
import re
import sys

error_log_path = os.path.expanduser("~/.ultrastardx/logs/Error.log")

song_dir = ""

skip_non_auto = False

dry_run = False

remove_empty_fields = True

remove_missing_videos = True

handle_video_if_audio_missing = False


class Error:
    def __init__(self):
        self.wont_fix = True

    def __repr__(self):
        return self.__str__()

    def fix(self, lines, path):
        pass


class UnknownError(Error):
    def __str__(self):
        return "Unknown error"

    # can't fix
    pass


class GeneralError(Error):
    def __str__(self):
        return "General error"

    # can't fix
    pass


def glob_make_case_insensitive(pattern):
    return "".join(map(lambda c: f"[{c.lower()}{c.upper()}]" if c.isalpha() else c, pattern))


def glob_extensions(path, extensions):
    return sum(
        [glob.glob(f"{glob.escape(path)}/*.{glob_make_case_insensitive(extension)}") for extension in extensions], [])


class NoAudioError(Error):
    def __init__(self):
        super().__init__()
        self.wont_fix = False

    def __str__(self):
        return "No audio"

    # find file (and ask if its correct) or can't fix
    def fix(self, lines, path):
        for i in range(len(lines)):
            if lines[i].upper().startswith("#MP3:"):
                audio_files = glob_extensions(os.path.dirname(path), ["mp3", "ogg", "wav", "m4a"])
                if len(audio_files) > 0:
                    print("Found audio files in folder:")
                else:
                    audio_files = glob_extensions(os.path.dirname(path),
                                                  ["mp4", "avi", "flv", "ts", "webm", "mkv", "mov", "wmv", "mpg",
                                                   "mpeg", "divx"])
                    if len(audio_files) > 0:
                        print("Did not find any audio files, but found video files in folder:")
                    else:
                        return
                for j in range(len(audio_files)):
                    print(f"[{j}] {os.path.basename(audio_files[j])}")
                selection = input(f"Select file to overwrite tag ({lines[i].strip()}) with:")
                if selection.isdecimal():
                    lines[i] = f"#MP3:{os.path.basename(audio_files[int(selection)])}\n"
                return True


class NoVideoError(Error):
    def __init__(self):
        super().__init__()
        self.wont_fix = False

    def __str__(self):
        return "No video"

    # find file (and ask if its correct) or can't fix
    def fix(self, lines, path):
        for i in range(len(lines)):
            if lines[i].upper().startswith("#VIDEO:"):
                video_files = glob_extensions(os.path.dirname(path),
                                              ["mp4", "avi", "flv", "ts", "webm", "mkv", "mov", "wmv", "mpg",
                                               "mpeg", "divx"])
                if len(video_files) > 0:
                    print("Found video files in folder:")
                elif remove_missing_videos:
                    lines.pop(i)
                    return False
                else:
                    return
                for j in range(len(video_files)):
                    print(f"[{j}] {os.path.basename(video_files[j])}")
                selection = input(f"Select file to overwrite tag ({lines[i].strip()}) with:")
                if selection.isdecimal():
                    lines[i] = f"#VIDEO:{os.path.basename(video_files[int(selection)])}\n"
                return True


class AudioMissingError(Error):
    def __init__(self):
        super().__init__()
        self.wont_fix = False

    def __str__(self):
        return "Audio missing"

    # check MP3 tag, if missing: add and apply NoAudioError
    def fix(self, lines, path):
        for i in range(len(lines)):
            if lines[i].upper().startswith("#MP3:"):
                return  # NoAudioError exists and will be fixed separately
        lines.insert(0, "#MP3:\n")
        NoAudioError().fix(lines, path)
        return False


class SentenceWithoutNoteError(Error):
    def __init__(self, line):
        super().__init__()
        self.wont_fix = False
        number_end = line.find(":", line.find(":") + 1)
        number_start = line.rfind(" ", 0, number_end)
        line_number = line[number_start + 1:number_end]
        if line_number == "E":
            self.line_number = -1
        else:
            self.line_number = int(line_number)

    def __str__(self):
        return f"Sentence without note (line {self.line_number})"

    # delete sentence
    def fix(self, lines, path):
        if self.line_number == -1:
            i = len(lines) - 1
            while i >= 0 and lines[i].strip() != "E":
                i -= 1
            self.line_number = i
        if self.line_number < 0:
            # no 'E'
            lines.append("E")
            return False
        lines.pop(self.line_number - 1)
        return False


class EmptyFieldError(Error):
    def __init__(self, line):
        super().__init__()
        self.wont_fix = skip_non_auto
        field_start = line.find("\"")
        field_end = line.find("\"", field_start + 1)
        self.field_name = line[field_start + 1:field_end]

    def __str__(self):
        return f"Empty field ({self.field_name})"

    # ask for content or remove if still empty
    def fix(self, lines, path):
        if skip_non_auto:
            return
        value = ""
        if not remove_empty_fields:
            value = input(f"Empty field \"{self.field_name}\". Enter value (leave empty to remove):")
        for i in range(len(lines)):
            if lines[i].upper().startswith(f"#{self.field_name}:"):
                if value == "":
                    lines.pop(i)
                    return False
                else:
                    lines[i] = f"#{self.field_name}:{value}\n"
                    return True


class EmptyLinesOrNoBPMError(Error):
    def __init__(self):
        super().__init__()
        self.wont_fix = False

    def __str__(self):
        return "Empty lines or no BPM"

    # search for bpm tag. if missing, ask for value. find and remove empty lines.
    # hint: this can also happen because some random line starts with a Byte Order Mark.
    def fix(self, lines, path):
        result = None
        found_bpm = False
        bpm_line = -1
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == "":
                lines.pop(i)
                result = False
            elif lines[i].upper().startswith("#BPM:"):
                found_bpm = True
                if not lines[i][5:-1].replace('.', '', 1).isdecimal():
                    bpm_line = i
        if not found_bpm:
            if skip_non_auto:
                return result
            if bpm_line >= 0:
                bpm = input(f"Invalid BPM Tag ({lines[bpm_line][:-1]}) found. Please enter BPM:")
                lines[bpm_line] = f"#BPM:{bpm}\n"
                if result is None:
                    result = True
            else:
                bpm = input("No BPM Tag found. Please enter BPM:")
                if bpm.replace('.', '', 1).isdecimal():
                    lines.insert(0, f"#BPM:{bpm}\n")
                    result = False
        return result


class NoLinebreaksError(Error):
    def __str__(self):
        return "No linebreaks"

    # can't fix
    pass


class StartsWithEmptyLineError(Error):
    def __init__(self):
        super().__init__()
        self.wont_fix = False

    def __str__(self):
        return "Starts with empty line"

    # remove first line
    def fix(self, lines, path):
        if lines[0].strip() == "":
            lines.pop(0)
            return False


class CharacterExpectedError(Error):
    def __init__(self, line):
        super().__init__()
        self.wont_fix = False
        filename_end = line.find("\"", line.find("\"") + 1)
        number_end = line.find(":", filename_end)
        self.line_number = int(line[filename_end + 10:number_end])

    def __str__(self):
        return f"Character expected (line {self.line_number})"

    # if line is "[-:F*]###...", replace with "[-:F*] ###...",
    # or line starts with "-" and ends with whitespace, remove the whitespace.
    # otherwise can't fix
    def fix(self, lines, path):
        if lines[self.line_number - 1][0] in ["-", ":", "F", "*"] and \
                lines[self.line_number - 1][1:].split(" ")[0].strip().isdecimal():
            lines[self.line_number - 1] = f"{lines[self.line_number - 1][0]} {lines[self.line_number - 1][1:]}"
            return True
        if lines[self.line_number - 1][0] == "-" and \
                len(lines[self.line_number - 1]) != len(lines[self.line_number - 1].strip()):
            lines[self.line_number - 1] = lines[self.line_number - 1].strip()
            return True


class ZeroLengthNoteError(Error):
    def __init__(self, line):
        super().__init__()
        self.wont_fix = False
        self.line_number = int(line[line.rfind("\"") + 10:line.rfind(":")])

    def __str__(self):
        return f"Zero-length note (line {self.line_number})"

    # set note length to 1 and replace first char with f
    def fix(self, lines, path):
        line_parts = lines[self.line_number - 1].split(" ")
        line_parts[0] = "F"
        line_parts[2] = "1"
        lines[self.line_number - 1] = " ".join(line_parts)
        return True


class NoNotesError(Error):
    def __str__(self):
        return "No notes"

    # can't fix
    pass


class IntegerExpectedError(Error):
    def __init__(self, line):
        super().__init__()
        self.line_number = int(line[line.rfind("in line ") + 8:line.rfind(",")])

    def __str__(self):
        return f"Integer expected (line {self.line_number})"

    # can't fix
    pass


class StringExpectedError(Error):
    def __init__(self, line):
        super().__init__()
        self.wont_fix = False
        self.line_number = int(line[line.rfind("in line ") + 8:line.rfind(",")])

    def __str__(self):
        return f"String expected (line {self.line_number})"

    # might contain empty lines
    def fix(self, lines, path):
        return EmptyLinesOrNoBPMError().fix(lines, path)


def main():
    error_count = 0
    fix_counter = 0

    error_log_file = open(error_log_path, 'r')

    error_log_lines = [x[:-1] for x in error_log_file.readlines()]

    error_map = {}

    print("Extracting txts with errors...", file=sys.stderr, flush=True)
    for line in error_log_lines:
        txt_end = -1
        for match in re.finditer("\\.txt", line, flags=re.IGNORECASE):
            txt_end = match.start()
        if txt_end == -1:
            continue

        line_error = UnknownError()
        txt_start = max(line.rfind("/", 0, txt_end), line.rfind("\"", 0, txt_end))
        # non-exhaustive list of errors with identifiable source and how they can be detected in the log
        if line.startswith("ERROR:  Can't find audio file in song"):
            line_error = NoAudioError()
        if line.startswith("ERROR:  Can't find video file in song"):
            line_error = NoVideoError()
        if line.startswith("ERROR:  MP3 tag/file missing"):
            line_error = AudioMissingError()
        if line.startswith("ERROR:  AnalyseFile failed for"):
            line_error = GeneralError()
        if line.startswith("ERROR:  Error loading Song, sentence w/o note found"):
            line_error = SentenceWithoutNoteError(line)
            txt_start = max(line.rfind("/", 0, txt_end), line.find(":", 10, txt_end) + 1)
        if line.startswith("INFO:   Empty field"):
            line_error = EmptyFieldError(line)
        if line.startswith("ERROR:  File contains empty lines or BPM tag missing"):
            line_error = EmptyLinesOrNoBPMError()
        if line.startswith("ERROR:  Error loading file: Can't find any linebreaks"):
            line_error = NoLinebreaksError()
        if line.startswith("ERROR:  File starts with empty line"):
            line_error = StartsWithEmptyLineError()
        if line.startswith("ERROR:  Could not load txt File, no notes found"):
            line_error = NoNotesError()
        if line.endswith("[TSong.ParseLyricCharParam]"):
            line_error = CharacterExpectedError(line)
        if line.endswith("found note with length zero -> converted to FreeStyle [TSong.LoadSong]"):
            line_error = ZeroLengthNoteError(line)
        if line.endswith("Integer expected"):
            line_error = IntegerExpectedError(line)
        if line.endswith("String expected"):
            line_error = StringExpectedError(line)
        txt_name = line[txt_start + 1:txt_end + 4]

        if txt_name not in error_map:
            error_map[txt_name] = []

        error_map[txt_name].append(line_error)
        error_count += 1

    print(f"{len(error_map.keys())} unique txt names with {error_count} errors", file=sys.stderr, flush=True)
    print("Checking existence of txts with errors...", file=sys.stderr, flush=True)
    for txt in error_map.keys():
        print(f"{txt} - {error_map[txt]}")
        if all([error.wont_fix for error in error_map[txt]]):
            continue
        txt_files = glob.glob(f"{glob.escape(song_dir)}/**/{glob.escape(txt)}", recursive=True)
        if len(txt_files) > 1:
            print(f"Not Unique (requires error detection for fixing): {txt}", file=sys.stderr, flush=True)
        elif len(txt_files) == 0:
            print(f"Not Found (possible bug or file deleted): {txt}", file=sys.stderr, flush=True)
        else:
            if dry_run:
                continue
            system_encoding = False
            try:
                txt_file = open(txt_files[0], 'r', encoding="Windows-1252")
                txt_lines = txt_file.readlines()
                txt_file.close()
            except UnicodeDecodeError:
                txt_file = open(txt_files[0], 'r')
                txt_lines = txt_file.readlines()
                txt_file.close()
                system_encoding = True
            if len(txt_lines) == 0:
                print(f"Empty: {txt}")
                continue
            any_fixes_applied = False
            for error in error_map[txt]:
                if not handle_video_if_audio_missing and type(error) == NoVideoError:
                    if any([type(e) == NoAudioError or type(e) == AudioMissingError for e in error_map[txt]]):
                        continue
                result = error.fix(txt_lines, txt_files[0])
                if result is not None:
                    any_fixes_applied = True
                    if not result:
                        print("Line numbers changed. Regenerate Errorlog before running again,"
                              " otherwise files might get corrupted!",
                              file=sys.stderr, flush=True)
                        break
            if any_fixes_applied:
                if system_encoding:
                    txt_file = open(txt_files[0], 'w')
                else:
                    txt_file = open(txt_files[0], 'w', encoding="Windows-1252")
                txt_file.writelines(txt_lines)
                txt_file.close()
                fix_counter += 1
    print(f"Applied fixes to {fix_counter} files.", file=sys.stderr, flush=True)


if __name__ == '__main__':
    main()
