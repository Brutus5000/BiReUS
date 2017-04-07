from pathlib import Path


class NotificationService(object):
    def __init__(self, repository):
        self.repository = repository
        self._indent = 0

    def _rel(self, path: Path) -> str:
        """
        Calculates the relative path inside a repository
        :param path: absolute path
        :return: relative path to repository root
        """
        try:
            return str(path.relative_to(self.repository.absolute_path))
        except ValueError:
            return "[ARCHIVE] " + str(path)

    def _inc(self) -> None:
        """
        Increase indentation by one level
        :return: None
        """
        self._indent += 4

    def _dec(self) -> None:
        """
        Decrease indentation by one level
        :return: None
        """
        self._indent -= 4

    def notify(self, message: str, line_break: bool = True, indent: bool = True) -> None:
        """
        Show a message to the user
        Overwrite this message to adapt to your needs
        :param message: str
        :param line_break: bool
        :param indent: bool
        :return: None
        """
        if indent:
            indent_chars = ' ' * self._indent
        else:
            indent_chars = ''

        if line_break:
            print(indent_chars + message)
        else:
            print(indent_chars + message, end='')

    def error(self, message: str) -> None:
        self.notify(message)

    def begin_checkout_version(self, version: str) -> None:
        self.notify("Checking out version %s (current version: %s)" % (version, self.repository.current_version))

    def finish_checkout_version(self, version: str) -> None:
        self.notify("Version %s is now checked out " % version)

    def checked_out_already(self) -> None:
        self.notify("No patching necessary - you are already on the desired version")

    def version_unknown(self, version: str) -> None:
        self.notify("Version %s does not exist")

    def no_patch_path(self, version: str) -> None:
        self.notify("There is no patching path to reach version %s from %s. Please contact the administrators!" % (
            version, self.repository.current_version))

    def begin_apply_patch(self, version_from: str, version_to: str):
        self.notify("Applying patch %s -> %s" % (version_from, version_to))
        self._inc()

    def finish_apply_patch(self, version_from: str, version_to: str):
        self._dec()
        self.notify("Patch %s -> %s applied" % (version_from, version_to))

    def begin_download_patch(self, url: str) -> None:
        self.notify("Downloading patch from %s ... " % url, line_break=True)

    def finish_download_patch(self, url: str) -> None:
        self.notify("done", indent=False)

    def begin_patching_directory(self, path: Path) -> None:
        self.notify("Patching directory %s ... " % self._rel(path))
        self._inc()

    def finish_patching_directory(self, path: Path) -> None:
        self._dec()
        self.notify("Patching directory %s finished" % self._rel(path))

    def begin_patching_file(self, path: Path) -> None:
        self.notify("Patching file %s ... " % self._rel(path), line_break=False)

    def finish_patching_file(self, path: Path) -> None:
        self.notify("done", indent=False)

    def begin_adding_file(self, path: Path) -> None:
        self.notify("Adding file %s ... " % self._rel(path), line_break=False)

    def finish_adding_file(self, path: Path) -> None:
        self.notify("done", indent=False)

    def begin_removing_file(self, path: Path) -> None:
        self.notify("Removing file %s ... " % self._rel(path), line_break=False)

    def finish_removing_file(self, path: Path) -> None:
        self.notify("done", indent=False)

    def begin_patching_archive(self, path: Path) -> None:
        self._inc()
        self.notify("Begin patching archive file %s" % self._rel(path))

    def finish_patching_archive(self, path: Path) -> None:
        self.notify("Finished patching archive file %s" % self._rel(path))
        self._dec()

    def found_patch_path(self, patch_path):
        message = "The following patches will be applied: "

        i = 1
        while i < len(patch_path):
            if i > 1:
                message += ", "
            version_from = patch_path[i - 1]
            version_to = patch_path[i]

            message += "%s -> %s" % (version_from, version_to)

            i += 1

        self.notify(message)

    def crc_mismatch(self, path: Path) -> None:
        self.notify("CRC mismatch - fallback to download from source")
