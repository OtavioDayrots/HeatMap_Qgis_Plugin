class ExportMapOptions:
    def __init__(self, fmt="PNG", dpi=300, include_border=True, include_scalebar=True, include_timestamp=True, include_legend=True):
        self.fmt = fmt
        self.dpi = int(dpi)
        self.include_border = bool(include_border)
        self.include_scalebar = bool(include_scalebar)
        self.include_timestamp = bool(include_timestamp)
        self.include_legend = bool(include_legend)