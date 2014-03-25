from ajenti.api import *  # noqa
from ajenti.plugins import *  # noqa

info = PluginInfo(
    title='Transmission',
    icon='download-alt',
    dependencies=[
        PluginDependency('main'),
        BinaryDependency('transmission-daemon'),
        ModuleDependency('transmissionrpc'),
    ],
)

def init():
    import main
