from arctic import Arctic

from .config import AdagioConfig

arctic_store = Arctic(AdagioConfig.arctic_host)


def get_library(library_name):
    """ Return arctic library. Library is initialised if not exists
    :rtype: arctic.store.version_store.VersionStore
    """
    libraries = arctic_store.list_libraries()
    if library_name not in libraries:
        arctic_store.initialize_library(library_name)

    return arctic_store[library_name]
