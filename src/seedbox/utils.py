import io
import tarfile


class TarFile(tarfile.TarFile):
    def adddata(self, path, data):
        info = tarfile.TarInfo(path)
        info.size = len(data)
        self.addfile(info, io.BytesIO(data))
