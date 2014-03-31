from ajenti.api import *  # noqa
from ajenti.plugins import *  # noqa

info = PluginInfo(
    title='Transmission',
    icon='download-alt',
    dependencies=[
        PluginDependency('main'),
        PluginDependency('models'),
        BinaryDependency('transmission-daemon'),
    ],
)

def init():
    import main
    import dom
