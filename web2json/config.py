"""Configuration settings and constants."""

VERSION = "1.0.0"
PROGRAM = "web2json"

# Request settings
MAX_WORKERS = 5
REQUEST_TIMEOUT = 10
MAX_URL_LENGTH = 2048
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"

# File settings
DEFAULT_OUTPUT_FOLDER = "fetched_jsons"
MAX_FILENAME_LENGTH = 255
MAX_PATH_LENGTH = 50
DEFAULT_ENCODING = 'utf-8'

# HTML elements configuration
STYLE_TAGS = {
    'b', 'strong', 'i', 'em', 'sup', 'sub', 'u', 'mark',
    'small', 's', 'del', 'ins', 'abbr', 'cite', 'q', 'dfn',
    'time', 'code', 'var', 'samp', 'kbd', 'span'
}

STRUCTURAL_TAGS = {
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'header', 'footer', 'main', 'article', 'section',
    'aside', 'nav', 'p', 'pre', 'blockquote', 'div',
    'address', 'ul', 'ol', 'dl', 'dt', 'dd', 'menu',
    'table', 'caption', 'thead', 'tbody', 'tfoot',
    'tr', 'td', 'th', 'colgroup', 'col',
    'figure', 'figcaption', 'picture', 'audio', 'video',
    'canvas', 'svg', 'form', 'fieldset', 'legend',
    'details', 'summary', 'dialog'
}