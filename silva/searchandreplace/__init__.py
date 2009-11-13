

def initialize(context):
    import SearchReplaceService

    context.registerClass(
        SearchReplaceService.ServiceSearchReplace,
        constructors = (
            SearchReplaceService.manage_addServiceSearchReplaceForm,
            SearchReplaceService.manage_addServiceSearchReplace),
        icon = 'searchreplaceservice.png')
