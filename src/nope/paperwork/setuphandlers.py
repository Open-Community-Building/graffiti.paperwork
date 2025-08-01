from interaktiv.framework.products import installer


def post_install(context):
    pass


def uninstall(context):
    """Uninstall script"""
    # Keep this list in sync with 'metadata.xml' of nope.paperwork
    uninstall_products = ["nope.paperwork"]
    uninstall_products = list(set(uninstall_products) - {"nope.paperwork"})
    installer().uninstall_products(uninstall_products)
