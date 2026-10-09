"""Fit the full widescreen PDF once; clip its reserved caption band."""
def page_layout(width, height):
    wide = abs(width / height - 16 / 9) < .003
    return dict(profile='video-16x9' if wide else 'legacy',
                width=1920, height=1080 if wide else 900, content_height=900,
                header_bottom=(32 + 13 * 96 / 25.4) * width / 1920 if wide else 59,
                body_bottom=height * 876 / 1080 if wide else height - 23)
