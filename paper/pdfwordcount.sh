#!/bin/sh
# Counts the main body of the built PDF the way a plain word counter does:
# everything from the title up to the References heading. Appendix and
# bibliography sit after that point and are excluded.
pdftotext "${1:-main.pdf}" - | awk '/^References$/{exit} {print}' | wc -w
