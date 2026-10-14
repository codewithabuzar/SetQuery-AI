"""PDF canvas with accurate total-page numbering."""

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor


class NumberedCanvas(canvas.Canvas):
    """Draw Page X of Y after all pages are known."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_pages = []

    def showPage(self):
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_pages)

        for number, state in enumerate(
            self._saved_pages,
            start=1,
        ):
            self.__dict__.update(state)

            self.setFont("Helvetica", 8)
            self.setFillColor(HexColor("#667085"))

            width, _ = self._pagesize

            self.drawRightString(
                width - 44,
                32,
                f"{number} / {total}",
            )

            super().showPage()

        super().save()
