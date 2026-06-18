from __future__ import annotations

from html import escape
from typing import Sequence

import streamlit as st

from nav_config import PageSpec, SectionSpec


BRAND_GREEN = "#1DA539"
SIDEBAR_SCALE = 1.23

# Change these numbers when you want to adjust each sidebar text level.
ROOT_TEXT_SIZE = 18
SECTION_TEXT_SIZE = 19
CHILD_TEXT_SIZE = 18

ROOT_ICON_SIZE = 23
SECTION_ICON_SIZE = 24
CHILD_ICON_SIZE = 23

BRAND_KICKER = "\u5927\u6a39\u91ab\u85e5\u80a1\u4efd\u6709\u9650\u516c\u53f8"
BRAND_TITLE = "\u5927\u8c50\u7269\u6d41\u90e8"
BRAND_SUBTITLE = "\u4f5c\u696d\u5e73\u53f0"
BRAND_IMAGE_DATA_URI = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAEIAAABCCAYAAADjVADoAAAQAElEQVR4AexZCZhUxbX+q+7Wt7tn"
    "pmeHgUFB2QWDRHBBEAlG0Q8MweRpIhIfLiAYIK4YERcCSqJE0ACKG4aEoFnUiCJu7BqIsi8ygMMM"
    "zD7T6+271jt3QF+esg0w+JKPO1V9u6vqnKrz19mqhuP004jAaSAaYQBOA3EaiIMIHHyd1ojTQBxE"
    "4ODrtEb8fwPi/EeHFPf+1bVdDq7rlL++VY3oNmXI9Rf/dbTI+d0VoiTfLv08K7a59ayrRd8/3iJ6"
    "Th92z6lE41sD4qqFY/fWZNu/XxPdgfp8D/XhNFULVYEUNhp7sRH7pg14fazXffoNoVMByLcCxKA/"
    "3b7+nw3bW8dCKbhIQTgG1QQENyFJFpJ2FFJREKuqtjDRwkl0vHtwRnODccqBaHf/wOvWVW/vHtUM"
    "pBUbUoABZgJQGWSNgysehOzAkC0YuoNS0YDC8wo/+Y8DIrtb6wX1ARKShHXTMbiuAygKIDE4LrU7"
    "aXgKA+w0yW4hylJYX7+r05njLjiTGpqt8GbjfAjG3SZfec226l2wFAcCJpScSOMoSVGBFAnuuhCM"
    "gUnUrMpAgADiNpwQR1anVg9Sa7OVUwpEVquc/o4MSKEAwGjT43GAjjuuJQAmQ9J0BFQVwiYtMQiY"
    "lAGmajAsA8HW2SPQjE+zAHHh/YOvHfqnO/858OVR4jtTBothr04Q/V64cb2VLd2hZGlwjRR8wbmk"
    "ggvafhJcCofhmiYMw4Aia4SP3AiCMFPgGsOm8p3osWi4aPfk1eKCmdeLIXNui3/v4evm9fzZZeed"
    "DHxOKhB5d1+c0X/hGFFa5Pzp3eq1PT5xPsfuwhiWRtfhU7Gn+8bkbiREkoRkkFwJsi2BewAYIxDI"
    "YUoCcjAAT2LURAB5vqZ4cLiFlG5jc7IUVRkmtmq1WIad4Q351TdVfIet+87MoUtwgg8/QfqvyLtM"
    "7qLmd2gdW1u3BeVqA1CsI6rUIxpMooFyg5hOu62QykskOSMy4U9NwroMKpkEU8lcJAlOIgXLMBuB"
    "EJYNMAKDu3AVC5ZiI6mZiOkGGkIGasJJVGamUBaMDmw37fuf4QQefgK0/4e0ZZcL47Wogxe0oWQw"
    "xOtKAT80UqbAQMLQ+8D2ExnjcGUGSybBff/gcIi4AZCZyBk5ULQQPF8bZJUG+4XA83kwApK54MKv"
    "DhgcyKqEBjeF2gg7N+f+/pP80cdTTwoQfaZeddOmil1qjKfh0EJtxwQyKCF0KU/wANmjj8ZKgFCB"
    "oN+clkt2oekqJNIENEYIDiedhks+A44HTkCRtDTwYBFoVBAwoodfAUc48HQJ6YgEURR6CMf5+Ms5"
    "TtL/JQsWFc9OSCpYMItkVAGT2JL9w5Kg2xwB2nHFYWCuB8kX0N9tQWpPQtgemUyyDn5CBe7Azx90"
    "TQUPqPBsE41AMAAeA/c4mKAfpDkeRRmXc8o9PFAzTDsOO8zQ8vbet+A4Hn4cNN8gKaurVmxSdSOZ"
    "hKxo0Hx7t13IgSAELVhAArlBcCiQSQjZX7nLwCyGbKEjF5nQYxxqnYsCQd+jLqSYA00irRIKAAms"
    "0adwCOLi0qoP/gSFGDSCFVaRSNZCLwz/FMfx8OOg+QZJ2oshoBMrUlGDdsb0aLfJ8zu2haQiI0GZ"
    "oyMpcJlGgmiQXB2SFYBu6M/opeKelvuDdxeVq/cUlan3FVcEJxZWqg+091pMk2s8wNFoPpXoZKqs"
    "cfcJF4AyU1IR+ioAywJMA3pQAQvhEiJocuFNpjgEQUIxkPKipL5JcJUW5js1Um1aJSATgUSV0wdV"
    "RloB2k6Zwidz2OyySe89vumBN6eX/PKDx/c8tHLaugfenrp50tJHt4x67b4I18FpLMgceGPlPiOq"
    "VBrb6W05ZFUSKAGBonKkVJcam158zk2n+heK/F/3vtcPZ45K9qw6cJkFJtFiLMoXGO0op+8+GHBo"
    "1+ik6f9mDglowWFpM//pS8Mt5lwusmf3EYWz+4qzZ39ftHy4d09/CpUL8isW4AJhpkBKOlAdDtlV"
    "ideBty5pUBgA0sCYFYcR8FD0aJ/rqKVJ5biBKB5zcVGPV64TRgafavphkhZCKgEIQUXQ4qkSDiBf"
    "AT8foB1VNBUumY3v6bMywxCKy6vleCAVshEL2KhT06ihQ5aIBMO+FKloPUJEA+EhaSQRzCKfwQWc"
    "dAoqmZxHUSmVNmBROAVFmEBmEKZOlpIjLygY3/stn8ex1uMComj0+cVa9/zyjfWlsAMBcB4kAAIk"
    "vAbmqOCeAkaVe7RzUCk86pAJFDtpQtCiXYoWiVQcGq0y7GkcNoOmBuFHgjRIUNaIKgqzc5GIxehs"
    "IsPNkNCQrIRFO44QTaVYlGukwEIqnIBM0qeQTidhcRspGiN3yLkyPP68pTTFMRV+TKO+NijvvDNL"
    "96MBUq4Gh3IBkq4x8nGHkUuQIEGhqkEhIOQkEE7JyIwraCmykO9kIM/SkZ/WoUeZHZR1JiyPTNyE"
    "pBGYSgC2ZUqgR9SaKLJDyKoTiKRVqCKMLFNF0AvArUuCZ0XgMg+CTq3IzABkDj+iGJKJShaF3rFg"
    "gD6ux9+I1VELP+qIrw3o/sTQVz9P7oetOzCdOO28CYXuFGS/UtLEyCJAZiAozHFyiB0z2qxtbWb2"
    "6YyCvnQl1a9NfbBf4V65X+u9cp+qu1eVGNVxRyetIhIISYbtf5EJEJo3VM/6FJdJFxdtcS7O/czs"
    "c9a+cL8WJWzAmUaLWUrgDHgUeeCRCGQmMD0QkkAsDoWSMzlPR7Uag9wxe3Dg1q6PELsjFuJyxP5v"
    "dNZr9g+l/CBc2Qa4S+rsHNgVRjvD/OEetZHq0lePnBzixp7No/68cuXoPy7/x51/XubXjVOWLFs+"
    "dfFKGoKsQDiQtJOAJGD7lzHEx3Ftxe9bM/3dlasfe3/VpidWryqZsWbl1slLlm2fvOT9Ai+4Dgly"
    "vmmaQFIB039rZB4ERjgIy0zBNBuAgEAq6CGnc6s7fX5Hqk0CovC2iwpiZJsJlobbUEt2LcGjRMom"
    "lTxQQaYCUk9SC1nAkh2oKm+c45o3xokOT18jCn83SISfHiiyn7tSZD5/uSgLx8qMoAlOWSHMOsoF"
    "CJOIujh7zvdF7jOXi9xZl1E0GSjy510hzpxztfCFcVK1Xk6QQZIcyloBjRMIcQMyaaFvpkowQN9c"
    "wtYBqSvIEgNFI3sPhP8cpvLDtB+yOam4ebZEqFtphFsUwKRzARixaKy0RiHgayo4AxgjTyEjpOkK"
    "6EnAQDxgoVJKIJHtoT7LQ0xNApkyPAnwjCjkSCZlh1GkeRrJDBe1QQP1uS4q9Tiq1RSqQOOJl66p"
    "3E7EKDEj7bMs+Km7oqjwHNIMWoOdTsGjSMMYa2yzSTWlDPksIj1sISkO2/eNDldORyWaCLIEkxIZ"
    "MAmNKuDJpJYOuMQhyQe+Iw2EyFkGOTkA4iQUyU7TDsIPtcJEY1xwBOFFSyBhoAThUKiVZRUWHdqE"
    "H2ZUEpTCKXQJUDV4/jzEy7NUoSlhkFMBaD7K1uHSH5eok1GVaA2aTucQQXmHBN3mCDZ6Yuo7TOGH"
    "aT9ks/Hk+nKvPuGFmAabrtEgSWCKAvKY0DIz4Zk2XMcByBr0YAjpFIU3t1FHyOPLipL0kGUqyLQC"
    "CNVZyBSkwoag8Rrg0pscJQdHppoBpyJKYyWqGp1BLITjQG5juk3TCUZXFTQXJ/wlwDYNWgqDY6aJ"
    "FyNeLkDsoIegaSGAopKbSpfhCA+xOkLvIboK7MAWNQHIoWz6kGg+A/ASMA1aKQcpiQIfCMNX9bAM"
    "g9O1NIDareUjOqLFr7smsqZ0i0Ue6RDXJ+fUigeDSfabAAECWwZsksqSwOrdBd1QNL7NXvXW4hIM"
    "71GfNaxtqTsov8K6GPQYRtyUwxJc2aRfJuTsDAjHhSYrIGogRHlNgMBNxhAj8w3oYex8ZtWrNPiw"
    "hZZ+2L5DdqRKqidqdY7HkgxwqHIP0OhNZgE6XgvPBsiB0tESDkzsqv2i3mf0yYTXXlp++yt3rRr/"
    "2i9X/vzVSWt/8dZDe+784GHO+BQv7dAQhjAtWAH9pbFwwx1vzNg4aencTQ+vmP/xfUtf2/jw+4s/"
    "m7JkFQ2EEfFEwqXd8Cyai8OhpIuTFnoUvl263YJBa/AjSUY+MngYLOWt8OmOVPmROg/VVzlv8xuh"
    "eqwqcDPAbQpdZOdIJKDRW5aInUJUdpxs3yMg0ohleD+NPNtX5M28TOQ+NVC0eOEakTubosCTfUSr"
    "py5tHU276UxyI7oiIxWPQaI7C9eyCV2g19Qh4swZV4i8pweIwmcHirwXvicCcy4SOyKJhUnSBlnX"
    "ARqqBIIQZFY2mUBGJB+g4z0MGXx/ihI3DbvveuOoJ1JaOS28iaXksRWXpLfX/KXQDCFoasgMFcBN"
    "WZRak2bYDhhXEEoLZAoVKfLYcQ2IBVw4uSoqjHIkIwxuREGSRyXIEc+i84J/ey3gIUA3VnqIYiNA"
    "snioD1DN9FCpp1CjxJDOZkh4acjQwRo8yIL8Fe2+TRsRzshGOmoiaOsoMsPoJhch/ekeQgZHfY4L"
    "CJ9r7fQ1Q8W26I2Fdh5EvQxZyoDEA2QRMiJ08umd3QmROvn9MMJwLRdqdghRi6wkopF/N2FSZGBK"
    "UKBF2PE4gxrUKQgwxBwDlmIzfw6XjvScMHG9FJkfOUBF+M1gloJ2ajEKaG5uKJB5GKqeTecSGyG6"
    "68gxAuho565Yf+tCtm/uuppGoqN88KP0H7G74onVL+++5Q2W+QW7OqcycG94P7u3sEobEyx1L3xv"
    "2AJWMmHZgGCZ95MOGe3gVSQRIlPyb6TkOhP5IoRQ0nNx7SLPdj1SbRKSc7jkb0zpwLQO/ffLH5vj"
    "haHHObSYjOxYAL0yOiKjQikqv+1N1jPQbvx3Q20/7JXZvvrCnM7LOqHllFaJjK4fjH75qOZwYJYD"
    "nycExAEWQPmvPvj7vvvefaz6rg8fq7j7w6fLJ69c82XfvvuXLtjx4/msQ1XW5X3UjssvUtrXfJe3"
    "W3RGPDK6bMLq8pYz+nZSpQAcw4GkqLDpaO3IblufvkCEh/cNd5g/JNwzOiy3DwYHeiy7MFZ0/sfD"
    "nmXrxr+y3x+zevhzM9YMndN/xVVPFaweNqffmpEv/fLjiYu2+H1NqScFiGOZ8LOHX3/3nRFz+v79"
    "R8/kL79twY8++sWi3/Wc01PJysvf4lDuoeoBuJQRIihDBPiMtk9c1mvFxL/Of23k3OEvXPt4ZP6Q"
    "x9miG57p99aE+WuPZb6mjjllQBxyYeFuVmWsDlAYLPIc8O897Rg4uY5kJvu442ODiw5J1wyNvBl4"
    "HhPLC+bfki636+AGAJn+SSP8NNsjUtdFKlqLNJ0aeVGg/MqnxmrU2uyFN/sMh5igz3M3bt+a2KnV"
    "eHXwNA/JZAIh8hMhut0KyWEoehAxN4ZSp5LyEPKYh+BxsptOORAD5o9csi1d2sGl0yXTXBh0vZar"
    "hdFW5K8oNiMTgw0SOEVLKDKSXgqfp75A/+dvrjrZgn+dxfuTKwAABBZJREFUH/96w0n//S8ML/rD"
    "yPmfpXYNrJVisJkBYZvQLI5ukbPLNg1/9ZJtI1+f2l46c36WnQXV1SDRP20aQhY+Te/Mv3DByA3/"
    "wuqkfz1lQFwx45a7avZW/DREuUQrORs5lG7mJYJoH2lT9v6QZ4u/lGzVLfOHdw62/SCvWkZenYK8"
    "dAAZpoq6vRXd+j1y3UtfjjvZ71MGxNvj5k7fcfebrHTM26zs5qVs/23LWcWYFWz99a9+BcKXwn10"
    "49zL9o17n1WO+pDtu20J2zv+Hbb9njfZRw/84cYvx5zs9ykD4lALH/CrH+S2n3pVu+/Ou7Zjz5k/"
    "7NRr5rVtL31wBMWRQ41u3rZTAsS5s37Y9ZzfX39Hp4U/fumc12/YcNbCoSL7mUvEhryGmvoWdsl6"
    "o3zbDj26dUc4tuvT1uVG9rOXC//OsmDOleKMF6/Z2/6FIR91nTv4pfPmDZ3Y+beXn9MckDQbEF0f"
    "uOj8tr+5aG7erN7xEvWLDXvwxW9LzD3DN1Vv7bbProGhukhxhy6PbLpICjbmEkkzBYs5iDspiDBH"
    "rYiiFg2tK1DXt0qPDt/plE5piCQ35s0+t7rlvJ4Lznmu/02XPnipfDKAOalAdHng3B6tp541U5+e"
    "v3V3m10ra1uX32wWVIS9QAVHcr+XbZpuGycoWsVDNe3tVlvbGi2WtkyF3sqqdBYXNSiLO1lZi9vF"
    "1MXnidy3W+13Fp+vFPzjjLi8OzfqNvDahBeWZC+ajAkrIOfVcuu6PUrVvLWFJRV5T7R+r+2jncac"
    "CCAnBYiuozvd3GpU8eq6dO0f4smGfpLjLUHMfkipMcdq+9M/KYiG+7eKhs/O3JAIld66jO8ctTh/"
    "46hFXTaNXTRw+9g3r9p774eDNt/x5qCNVDdPeGfQJ6P/duXmO98dtOa//9pr89il7faMW5VdOW6d"
    "lFfPW7ZnRRdEGrQbIongJD0uv8hS1i6Jo1OKJR4pnth2S9vRZ/26+8jerZsKygkB0eaqs6e1u6nD"
    "exYXxZk8fE/F9LJO0Udruyfuq/156he1U2pvr5hV8/PKBXvGbvtw+10bdu+cudO/ZGzqGr8av+Gu"
    "VVXrR73zSem4Va9Ujf34keox638Wv7OyV+W4slYF8ex2hWruCDlT2RTLqHo0f3jBi+1u6NLmK+Kj"
    "fDkuIDpc0W1C58E9/qs02OP+Xc/vGPD5rO2Ttj69ddlR5mrW7o3TNtavnbz2k8+nbXtxz5O7R1S/"
    "XDWCc0vp+IOONx3LxE0Coqhnz+AZl3RuuePtjU9sff3TP2LRIvdYJvm2xux8aWfJ9r9sf/5Y5m8S"
    "EPvWrUt9sXzr/mNh/O82pklA/LsJ15T1ngbiIFqngfjPB+KghMf4Oq0RB4E6DcRpIA4icPB1WiMO"
    "AvE/AAAA//+sdwQOAAAABklEQVQDABeFhv0yh2xPAAAAAElFTkSuQmCC"
)


def _link(spec: PageSpec, label: str, css_class: str) -> str:
    icon = escape(spec.icon or "")
    text = escape(label)
    href = "/" + escape(spec.url_path.lstrip("/"))

    text_sizes = {
        "nav-root": ROOT_TEXT_SIZE,
        "nav-section": SECTION_TEXT_SIZE,
        "nav-child": CHILD_TEXT_SIZE,
    }
    icon_sizes = {
        "nav-root": ROOT_ICON_SIZE,
        "nav-section": SECTION_ICON_SIZE,
        "nav-child": CHILD_ICON_SIZE,
    }
    text_size = text_sizes.get(css_class, CHILD_TEXT_SIZE)
    icon_size = icon_sizes.get(css_class, CHILD_ICON_SIZE)
    text_style = f"font-size:{text_size}px!important;font-weight:inherit!important;"
    icon_style = f"font-size:{icon_size}px!important;width:{icon_size + 4}px!important;"

    return (
        f'<a class="nav-link {css_class}" href="{href}" target="_self">'
        f'<span class="nav-icon" style="{icon_style}">{icon}</span>'
        f'<span class="nav-text" style="{text_style}">{text}</span>'
        "</a>"
    )


def render_sidebar(page_sections: Sequence[SectionSpec]) -> None:
    css = [
        "<style>",
        f":root{{--brand-green:{BRAND_GREEN};--sidebar-scale:{SIDEBAR_SCALE};}}",
        "section[data-testid='stSidebar']{background:#f8fafc!important;border-right:1px solid rgba(15,23,42,.10)!important;}",
        "section[data-testid='stSidebar'] *{font-family:'Noto Sans TC','Microsoft JhengHei',Arial,sans-serif!important;}",
        "section[data-testid='stSidebar'] [data-testid='stSidebarContent']{padding:4px 26px 30px 26px!important;}",
        "section[data-testid='stSidebar'] div[data-testid='stMarkdown']{margin:0!important;}",
        ".sidebar-scale-shell{zoom:var(--sidebar-scale);padding-top:14px;}",
        ".brand-block{display:flex;align-items:center;gap:16px;margin:0 0 22px 0;padding:0;background:transparent;border:0;box-shadow:none;}",
        ".brand-logo{width:58px;height:58px;object-fit:contain;display:block;filter:drop-shadow(0 3px 4px rgba(29,165,57,.18));}",
        ".brand-text{display:flex;flex-direction:column;gap:6px;color:#0f172a;white-space:nowrap;}",
        ".brand-kicker{font-size:15px;font-weight:900;line-height:1.05;color:#334155;}",
        ".brand-title{font-size:25px;font-weight:950;line-height:1.05;color:#0f172a;letter-spacing:.3px;}",
        ".brand-subtitle{font-size:16px;font-weight:900;line-height:1.05;color:#334155;}",
        ".nav-list{display:flex;flex-direction:column;gap:0;}",
        ".nav-link{display:flex;align-items:center;text-decoration:none!important;color:#0f172a!important;border-radius:8px;line-height:1.22!important;}",
        ".nav-link:hover{background:rgba(29,165,57,.08);}",
        ".nav-root{gap:10px;margin:0 0 25px 0;padding:9px 14px;background:linear-gradient(180deg,#39B54A,#2F9E44)!important;color:#fff!important;box-shadow:0 8px 16px rgba(29,165,57,.22);}",
        ".nav-root .nav-text,.nav-root .nav-icon{color:#fff!important;}",
        ".nav-section{gap:10px;margin:23px 0 13px 0;padding:5px 0;font-weight:950!important;}",
        ".nav-child{gap:10px;margin:0 0 13px 30px;padding:5px 4px;font-weight:850!important;}",
        ".nav-root .nav-text{font-weight:900!important;}",
        ".nav-section .nav-text{font-weight:950!important;}",
        ".nav-child .nav-text{font-weight:850!important;}",
        ".nav-icon{display:inline-flex;justify-content:center;align-items:center;line-height:1;flex:0 0 auto;}",
        "</style>",
    ]

    links = [
        '<div class="sidebar-scale-shell">',
        f'<div class="brand-block" aria-label="{escape(BRAND_KICKER)} {escape(BRAND_TITLE)} {escape(BRAND_SUBTITLE)}">',
        f'<img class="brand-logo" src="{BRAND_IMAGE_DATA_URI}" alt="憭扳邦?內">',
        '<div class="brand-text">',
        f'<div class="brand-kicker">{escape(BRAND_KICKER)}</div>',
        f'<div class="brand-title">{escape(BRAND_TITLE)}</div>',
        f'<div class="brand-subtitle">{escape(BRAND_SUBTITLE)}</div>',
        "</div>",
        "</div>",
        '<div class="nav-list">',
    ]

    for section in page_sections:
        if not section.pages:
            continue
        if not section.title:
            links.extend(_link(spec, spec.title, "nav-root") for spec in section.pages)
            continue
        links.append(_link(section.pages[0], section.title, "nav-section"))
        links.extend(_link(spec, spec.title, "nav-child") for spec in section.pages[1:])

    links.extend(["</div>", "</div>"])
    st.sidebar.markdown("\n".join(css + links), unsafe_allow_html=True)
