# -*- coding: utf8 -*-
from Plugins.Extensions.IPTVPlayer.tools.iptvtools import printDBG, printExc, byteify
from Plugins.Extensions.IPTVPlayer.components.ihost import CHostBase, CBaseHostClass
from Plugins.Extensions.IPTVPlayer.tools.iptvtypes import strwithmeta
from Plugins.Extensions.IPTVPlayer.libs.jsunpack import unpack, detect, get_packed_data
from Plugins.Extensions.IPTVPlayer.libs import ph
import base64, urllib, re, time, os, requests, hashlib, subprocess, threading, json, sys
try:
    from urllib.parse import quote_plus, urljoin, quote  # Python 3
except ImportError:
    from urllib import quote_plus  # Python 2
    from urlparse import urljoin
#################################################
def GetCookieDir(cookieFileName=''):
    try:
        COOKIE_PATH = '/tmp/IPTV_Cookies'
        if not os.path.exists(COOKIE_PATH):
            os.makedirs(COOKIE_PATH)
        if cookieFileName:
            return os.path.join(COOKIE_PATH, cookieFileName)
        return COOKIE_PATH
    except Exception as e:
        print('GetCookieDir Error:', e)
        return '/tmp'
def getDirectM3U8Playlist(m3u8Url, checkContent=False):
    import requests
    results = []
    try:
        printDBG('getDirectM3U8Playlist >>> ' + m3u8Url)
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': m3u8Url}
        data = requests.get(m3u8Url, headers=headers, timeout=10).text
        matches = re.findall(r'#EXT-X-STREAM-INF:[^\n]*RESOLUTION=(\d+x\d+)[^\n]*\n([^\n]+)', data)
        if matches:
            for res, link in matches:
                quality = res.split('x')[-1] + 'p'
                if not link.startswith('http'):
                    base = m3u8Url[:m3u8Url.rfind('/')+1]
                    link = base + link
                results.append({'name': quality, 'url': link})
        else:
            results.append({'name': 'direct', 'url': m3u8Url})
    except Exception as e:
        printDBG('getDirectM3U8Playlist error: %s' % e)
        results = [{'name': 'direct', 'url': m3u8Url}]
    return results
def printDBG(txt):
    try:
        print(txt)
    except:
        pass
def getinfo():
    info_ = {}
    name = 'Lodynet'
    hst = 'https://lodynet.watch'
    info_['host'] = hst
    info_['name'] = name
    info_['version'] = '5.0 26/10/2025'
    info_['dev'] = 'RGYSoft + Angel_heart'
    info_['desc'] = 'افلام و مسلسلات وبرامج وحفلات وكرتون وأغاني وممثلين'
    info_['icon'] = 'https://www.lodynet.co/wp-content/uploads/2015/12/logo-1.png'
    return info_
class Lodynet(CBaseHostClass):
    def __init__(self):
        params = {'history': 'lodynet.history','cookie': 'lodynet.cookie','history_store_type': False}
        CBaseHostClass.__init__(self, params)
        self.MAIN_URL = getinfo()['host']
        self.DEFAULT_ICON_URL = getinfo()['icon']
        self.USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    def searchItems(self):
        if self._historyLenTextFunction:
            return [
                {'category': 'search', 'title': 'بحث', 'search_item': True, },
                {'category': 'search_history', 'title': 'سجل البحث', 'desc': 'تاريخ العبارات التي تم البحث عنها.'},
                {'category': 'delete_history', 'title': 'حذف سجل البحث', 'desc': self._historyLenTextFunction}
            ]
        else:
            return []
    def getPage(self, url, params={}, post_data=None):
        HTTP_HEADER = {'User-Agent': self.USER_AGENT,'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8','Accept-Language': 'ar,en-US;q=0.7,en;q=0.3','Accept-Encoding': 'gzip, deflate','Referer': self.MAIN_URL}
        params.update({'header': HTTP_HEADER})
        url = self.encodeUrl(url)
        return self.cm.getPage(url, params, post_data)
    def getFullUrl(self, url):
        if not url:
            return self.DEFAULT_ICON_URL
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = self.MAIN_URL + url
        elif not url.startswith('http'):
            url = self.MAIN_URL + '/' + url
        if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
            if not url.startswith('http'):
                return self.DEFAULT_ICON_URL
        url = self.encodeUrl(url)
        return url
    def cleanHtmlStr(self, data):
        data = data.replace('&nbsp;', ' ')
        data = data.replace('&quot;', '"')
        data = re.sub(r'\s+', ' ', data)
        return data.strip()
    def encodeUrl(self, url):
        try:
            if isinstance(url, str):
                parts = re.match(r'^(https?://)(.*)$', url)
                if parts:
                    base, rest = parts.groups()
                    rest_encoded = quote(rest, safe="/:%#?=&")
                    return base + rest_encoded
            return url
        except Exception as e:
            printExc()
            return url
    def listsTab(self, tab, cItem):
        for item in tab:
            params = dict(cItem)
            params.update(item)
            self.addDir(params)
    def listMainMenu(self, cItem):
        printDBG('Lodynet.listMainMenu')
        MAIN_CAT_TAB = [
            {'category': 'sub_menu', 'title': 'مسلسلات', 'mode': '10', 'sub_mode': 0},
            {'category': 'sub_menu', 'title': 'أفلام', 'mode': '10', 'sub_mode': 1},
            {'category': 'list_items', 'title': 'برامج و حفلات', 'url': '/category/البرامج-و-حفلات-tv/'},
            {'category': 'sub_menu', 'title': 'أغاني', 'mode': '10', 'sub_mode': 2},
            {'category': 'list_items', 'title': 'المضاف حديثاً', 'url': '/', 'sub_mode': 'newly'},
        ]
        self.listsTab(MAIN_CAT_TAB, cItem)
        search_items = self.searchItems()
        for item in search_items:
            params = dict(cItem)
            params.update(item)
            self.addDir(params)
    def listSubMenu(self, cItem):
        printDBG('Lodynet.listSubMenu')
        gnr = cItem.get('sub_mode', '')
        if gnr == 0: 
            SUB_CAT_TAB = [
                {'category': 'list_items', 'title': 'مسلسلات هندية', 'url': '/category/مسلسلات-هندية-مترجمة/'},
                {'category': 'list_items', 'title': 'مسلسلات هندية مدبلجة', 'url': '/dubbed-indian-series-p5/'},
                {'category': 'list_items', 'title': 'مسلسلات ويب هندية', 'url': '/category/مسلسل-ويب-هندية/'},
                {'category': 'list_items', 'title': 'مسلسلات هندية 2020', 'url': '/release-year/مسلسلات-هندية-2020-a/'},
                {'category': 'list_items', 'title': 'مسلسلات هندية 2019', 'url': '/release-year/مسلسلات-هندية-2019/'},
                {'category': 'list_items', 'title': 'مسلسلات هندية 2018', 'url': '/release-year/مسلسلات-هندية-2018/'},
                {'category': 'list_items', 'title': 'مسلسلات تركية', 'url': '/category/مسلسلات-تركي/'},
                {'category': 'list_items', 'title': 'مسلسلات تركية مدبلجة', 'url': '/dubbed-turkish-series-g/'},
                {'category': 'list_items', 'title': 'مسلسلات كورية', 'url': '/korean-series-b/'},
                {'category': 'list_items', 'title': 'مسلسلات صينية', 'url': '/category/مسلسلات-صينية-مترجمة/'},
                {'category': 'list_items', 'title': 'مسلسلات تايلاندية', 'url': '/مشاهدة-مسلسلات-تايلندية/'},
                {'category': 'list_items', 'title': 'مسلسلات باكستانية', 'url': '/category/المسلسلات-باكستانية/'},
                {'category': 'list_items', 'title': 'مسلسلات آسيوية حديثة', 'url': '/tag/new-asia/'},
                {'category': 'list_items', 'title': 'مسلسلات مكسيكية', 'url': '/category/مسلسلات-مكسيكية-a/'},
                {'category': 'list_items', 'title': 'مسلسلات أجنبية', 'url': '/category/مسلسلات-اجنبية/'},
            ]
        elif gnr == 1:
            SUB_CAT_TAB = [
                {'category': 'list_items', 'title': 'افلام هندية', 'url': '/category/افلام-هندية/'},
                {'category': 'list_items', 'title': 'أفلام هندية مدبلجة', 'url': '/category/أفلام-هندية-مدبلجة/'},
                {'category': 'list_items', 'title': 'افلام هندية جنوبية', 'url': '/tag/الافلام-الهندية-الجنوبية/'},
                {'category': 'list_items', 'title': 'أفلام هندي 2025', 'url': '/release-year/أفلام-هندي-2025/'},
                {'category': 'list_items', 'title': 'أفلام هندي 2024', 'url': '/release-year/أفلام-هندي-2024/'},
                {'category': 'list_items', 'title': 'أفلام هندي 2023', 'url': '/release-year/أفلام-هندية-2023/'},
                {'category': 'list_items', 'title': 'أفلام هندي 2021', 'url': '/release-year/movies-hindi-2021/'},
                {'category': 'list_items', 'title': 'أفلام هندي 2020', 'url': '/release-year/افلام-هندي-2020-a/'},
                {'category': 'list_items', 'title': 'افلام هندي 2019', 'url': '/release-year/افلام-هندي-2019/'},
                {'category': 'list_items', 'title': 'افلام هندي 2018', 'url': '/release-year/افلام-هندي-2018/'},
                {'category': 'list_items', 'title': 'افلام هندي 2017', 'url': '/release-year/افلام-هندي-2017/'},
                {'category': 'list_items', 'title': 'افلام هندي 2016', 'url': '/release-year/2016/'},
                {'category': 'list_items', 'title': 'افلام هندية 4K', 'url': '/tag/افلام-هندية-مترجمة-بجودة-4k/'},
                {'category': 'list_items', 'title': 'أميتاب باتشان', 'url': '/actor/أميتاب-باتشان/'},
                {'category': 'list_items', 'title': 'اعمال شاروخان', 'url': '/actor/شاه-روخ-خان-a/'},
                {'category': 'list_items', 'title': 'أعمال سلمان خان', 'url': '/actor/سلمان-خان-a/'},
                {'category': 'list_items', 'title': 'أعمال عامر خان', 'url': '/actor/عامر-خان-a/'},
                {'category': 'list_items', 'title': 'أعمال شاهد كابور', 'url': '/actor/شاهيد-كابور/'},
                {'category': 'list_items', 'title': 'أعمال رانبير كابور', 'url': '/actor/رانبير-كابور/'},
                {'category': 'list_items', 'title': 'أعمال ديبيكا بادكون', 'url': '/actor/ديبيكا-بادكون/'},
                {'category': 'list_items', 'title': 'أعمال جينيفر ونجت', 'url': '/actor/جينيفر-ونجت/'},
                {'category': 'list_items', 'title': 'أعمال هريتيك روشان', 'url': '/actor/هريتيك-روشان/'},
                {'category': 'list_items', 'title': 'أعمال اكشاي كومار', 'url': '/actor/اكشاي-كومار/'},
                {'category': 'list_items', 'title': 'أعمال تابسي بانو', 'url': '/actor/تابسي-بانو/'},
                {'category': 'list_items', 'title': 'أعمال سانجاي دوت', 'url': '/actor/سانجاي-دوت-a/'},
                {'category': 'list_items', 'title': 'ترجمات احمد بشير', 'url': '/tag/جميع-الأفلام-في-هذا-القسم-من-ترجمة-أحمد/'},
                {'category': 'list_items', 'title': 'افلام تركية مترجم', 'url': '/category/افلام-تركية-مترجم/'},
                {'category': 'list_items', 'title': 'افلام باكستانية', 'url': '/tag/افلام-باكستانية-مترجمة/'},
                {'category': 'list_items', 'title': 'افلام اسيوية', 'url': '/category/افلام-اسيوية-a/'},
                {'category': 'list_items', 'title': 'افلام اجنبي', 'url': '/category/افلام-اجنبية-مترجمة-a/'},
                {'category': 'list_items', 'title': 'انيمي', 'url': '/category/انيمي/'},
            ]
        elif gnr == 2:
            SUB_CAT_TAB = [
                {'category': 'list_items', 'title': 'أغاني المسلسلات', 'url': '/category/اغاني/اغاني-المسلسلات-الهندية/'},
                {'category': 'list_items', 'title': 'تصاميم مسلسلات هندية', 'url': '/category/تصاميم-مسلسلات-الهندية/'},
                {'category': 'list_items', 'title': 'أغاني الأفلام', 'url': '/category/اغاني-الافلام/'},
                {'category': 'list_items', 'title': 'اغاني هندية mp3', 'url': '/category/اغاني/اغاني-هندية-mp3/'},
            ]
        self.listsTab(SUB_CAT_TAB, cItem)
    def listItems(self, cItem):
        printDBG("Lodynet.listItems [%s]" % cItem)
        url = cItem.get('url', '')
        page = cItem.get('page', 1)
        sub_mode = cItem.get('sub_mode', '')
        if not url.startswith('http'):
            url = self.getFullUrl(url)
        if page > 1:
            if '/page/' in url:
                url = re.sub(r'/page/\d+', '/page/' + str(page), url)
            else:
                url = url.rstrip('/') + '/page/' + str(page)
        sts, data = self.getPage(url)
        if not sts:
            return
        items = re.findall(r'<div class="ItemNewly">(.*?)</div>\s*</a>\s*</div>', data, re.S)
        items_added = 0
        for item in items:
            title_match = re.search(r'title="([^"]+)"', item)
            url_match = re.search(r'href="([^"]+)"', item)
            img_match = re.search(r'data-src="([^"]+)"', item)
            if not all([title_match, url_match, img_match]):
                continue
            title = title_match.group(1)
            item_url = url_match.group(1)
            img = img_match.group(1)
            item_url = self.getFullUrl(item_url)
            img = self.getFullUrl(img)
            desc = self.extractDescFromNewly(item)
            content_type = self.determineContentType(title, item_url)
            if content_type == 'series':
                params = {'category': 'list_episodes','title': title.strip(),'url': item_url,'desc': desc,'icon': img,'good_for_fav': True}
                self.addDir(params)
            else:
                params = {'category': 'video','title': title.strip(),'url': item_url,'desc': desc,'icon': img,'good_for_fav': True}
                self.addVideo(params)
            items_added += 1
        if sub_mode == 'newly' and items_added > 0:
            is_newly_section = (url == self.MAIN_URL + '/' or 
                               url.startswith(self.MAIN_URL + '/page/'))
            if is_newly_section:
                next_page = page + 1
                next_url = self.MAIN_URL + '/page/' + str(next_page) + '/'
                self.addDir({'category': 'list_items', 'title': '\\c00????00 الصفحة التالية (' + str(next_page) + ')','url': next_url,'icon': '','desc': '\\c00????00 الانتقال إلى الصفحة ' + str(next_page),'page': next_page,'sub_mode': 'newly'})
        more_match = False
        pick_up_order = ''
        pick_up_id = ''
        more_match1 = re.search(r'onclick="[^"]*GetMoreCategory\(\'([^\']+)\',\s*\'([^\']+)\'\)"', data)
        if more_match1:
            pick_up_order = more_match1.group(1)
            pick_up_id = more_match1.group(2)
            more_match = True
            printDBG("تم اكتشاف زر تحميل المزيد - النمط 1: order=%s, id=%s" % (pick_up_order, pick_up_id))
        if not more_match:
            more_match2 = re.search(r'onclick="[^"]*GetMoreCategory\(\'([^\']+)\',\s*\'([^\']+)\'\)[^"]*"', data)
            if more_match2:
                pick_up_order = more_match2.group(1)
                pick_up_id = more_match2.group(2)
                more_match = True
                printDBG("تم اكتشاف زر تحميل المزيد - النمط 2: order=%s, id=%s" % (pick_up_order, pick_up_id))
        if more_match and pick_up_order and pick_up_id:
            parent_id = ''
            parent_match1 = re.search(r"DataPosting\.append\('parent',\s*'(\d+)'\)", data)
            if parent_match1:
                parent_id = parent_match1.group(1)
                printDBG("تم اكتشاف parent_id - النمط 1: %s" % parent_id)
            if not parent_id:
                parent_match2 = re.search(r"append\('parent',\s*'(\d+)'\)", data)
                if parent_match2:
                    parent_id = parent_match2.group(1)
                    printDBG("تم اكتشاف parent_id - النمط 2: %s" % parent_id)
            type_match = re.search(r"DataPosting\.append\('type',\s*'([^']+)'\)", data)
            taxonomy_match = re.search(r"DataPosting\.append\('taxonomy',\s*'([^']+)'\)", data)
            data_type = type_match.group(1) if type_match else 'Category'
            taxonomy = taxonomy_match.group(1) if taxonomy_match else 'category'
            if parent_id:
                params = dict(cItem)
                params.update({'category': 'load_more','title': '\\c00????00 تحميل المزيد','pick_up_order': pick_up_order,'pick_up_id': pick_up_id,'parent_id': parent_id,'data_type': data_type,'taxonomy': taxonomy})
                self.addDir(params)
                printDBG("تم إضافة زر تحميل المزيد: order=%s, id=%s, parent=%s" % (pick_up_order, pick_up_id, parent_id))
            else:
                printDBG("لم يتم العثور على parent_id، لا يمكن إضافة زر تحميل المزيد")
        else:
            printDBG("لم يتم العثور على زر تحميل المزيد في الصفحة")
            if sub_mode != 'newly':
                next_match = re.search(r'class="next page-numbers".*?href="([^"]+)"', data)
                if next_match:
                    next_url = self.getFullUrl(next_match.group(1))
                    params = dict(cItem)
                    params.update({'category': 'list_items','title': '\\c00????00 الصفحة التالية', 'url': cItem['url'],'page': page + 1})
                    self.addDir(params)
    def listEpisodes(self, cItem):
        printDBG("Lodynet.listEpisodes [%s]" % cItem)
        url = cItem.get('url', '')
        if not url.startswith('http'):
            url = self.getFullUrl(url)
        sts, data = self.getPage(url)
        if not sts:
            self.addDir({'category': 'list_episodes', 'title': '\\c00????20خطأ في تحميل الصفحة','url': '','icon': '','desc': 'تعذر تحميل الصفحة، يرجى المحاولة لاحقاً'})
            return
        items_added = 0
        item_blocks = re.findall(r'(<div class="ItemNewly">.*?</div>\s*</a>\s*</div>)', data, re.S)
        if item_blocks:
            for item_block in item_blocks:
                title_match = re.search(r'<a title="([^"]+)"', item_block)
                url_match = re.search(r'href="([^"]+)"', item_block)
                img_match = re.search(r'data-src="([^"]+)"', item_block)
                if not all([title_match, url_match, img_match]):
                    continue
                title = title_match.group(1)
                item_url = url_match.group(1)
                img = img_match.group(1)
                if any(x in str(value) for value in [title, item_url, img] for x in ["+ CategoryItem.", "CategoryItem."]):
                    printDBG("تخطي عنصر غير صالح في الحلقات: " + title)
                    continue
                icon = self.getFullUrl(img)
                desc = self.extractDescFromNewly(item_block)
                self.addVideo({'category': 'video','title': title.strip(),'url': item_url,'desc': desc,'icon': icon,'good_for_fav': True})
                items_added += 1
        if items_added == 0:
            self.addDir({'category': 'list_episodes','title': '\\c00????20لا توجد حلقات متاحة','url': '','icon': '','desc': 'لا توجد حلقات متاحة لهذا المسلسل حالياً.\nقد يكون السبب:\n- الحلقات غير متوفرة بعد\n- المشكلة مؤقتة من الموقع\n- المسلسل قديم ولم يعد متاحاً'})
        more_match = re.search(r'<span id="ItemMoreBtn"[^>]*onclick="[^"]*GetMoreCategory\(\'([^\']+)\',\s*\'([^\']+)\'\)"', data)
        if more_match:
            pick_up_order = more_match.group(1)
            pick_up_id = more_match.group(2)
            parent_match = re.search(r"DataPosting\.append\('parent',\s*'(\d+)'\)", data)
            parent_id = parent_match.group(1) if parent_match else ''
            if pick_up_id and parent_id:
                self.addDir({'category': 'load_more_episodes','title': '\\c00FFFF00 تحميل المزيد من الحلقات','url': url,'icon': '','desc': '','pick_up_order': pick_up_order,'pick_up_id': pick_up_id,'parent_id': parent_id,'data_type': 'Category','taxonomy': 'category','is_episodes': True})
        else:
            next_match = re.search(r'class="nextpage-numbers".*?href="([^"]+)"', data)
            if next_match:
                next_url = self.getFullUrl(next_match.group(1))
                self.addDir({'category': 'list_episodes','title': '\\c00FFFF00الصفحة التالية للحلقات','url': next_url,'desc': '','icon': ''})
    def loadMore(self, cItem):
        printDBG("Lodynet.loadMore [%s]" % cItem)
        pick_up_order = cItem.get('pick_up_order', 'category')
        pick_up_id = cItem.get('pick_up_id')
        parent_id = cItem.get('parent_id')
        data_type = cItem.get('data_type', 'Category')
        taxonomy = cItem.get('taxonomy', 'category')
        is_episodes = cItem.get('is_episodes', False)
        if not pick_up_id or not parent_id:
            self.addDir({'category': 'list_items', 'title': 'لا يمكن تحميل المزيد', 'url': ''})
            return
        API_URL = self.MAIN_URL + "/wp-content/themes/Lodynet2020/Api/RequestMoreCategory.php"
        try:
            post_data = {"order": pick_up_order,"parent": parent_id, "type": data_type,"taxonomy": taxonomy,"id": pick_up_id}
            printDBG("Load More POST data: %s" % post_data)
            headers = {"User-Agent": self.USER_AGENT,"X-Requested-With": "XMLHttpRequest","Content-Type": "application/x-www-form-urlencoded; charset=UTF-8","Referer": self.MAIN_URL}
            import requests
            response = requests.post(API_URL, data=post_data, headers=headers, timeout=30)
            response_text = response.text
            if response_text and response_text.strip():
                try:
                    items = json.loads(response_text)
                    if isinstance(items, list) and items:
                        printDBG("تم استلام %d عنصر من API" % len(items))
                        valid_items = []
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            title = item.get("name", "")
                            url = item.get("url", "")
                            if not title or not url:
                                continue
                            valid_items.append(item)
                        for item in valid_items:
                            title = item.get("name", "")
                            url = item.get("url", "")
                            image = item.get("cover", "")
                            try:
                                if '\\u' in title:
                                    title = title.encode('utf-8').decode('unicode_escape')
                                elif '&#x' in title:
                                    import html
                                    title = html.unescape(title)
                            except Exception as e:
                                printDBG("خطأ في فك ترميز العنوان: %s" % str(e))
                            title = re.sub(r'[^\w\s\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', '', title)
                            if url and not url.startswith('http'):
                                if url.startswith('/'):
                                    url = self.MAIN_URL + url
                                else:
                                    url = self.MAIN_URL + '/' + url
                            icon = self.getFullUrl(image) if image else self.DEFAULT_ICON_URL
                            ribbon = item.get("ribbon", "")
                            ago = item.get("ago", "")
                            episode = item.get("episode", "")
                            # بناء الوصف
                            desc_parts = []
                            if ribbon: 
                                desc_parts.append('\\c00????00النوع: \\c00????FF' + ribbon)
                            if ago: 
                                desc_parts.append('\\c00????00وقت النشر: \\c00????FF' + ago)
                            if episode: 
                                desc_parts.append('\\c00????00الحلقة: \\c00????FF' + str(episode))
                            desc = '\n'.join(desc_parts) if desc_parts else ''
                            if is_episodes:
                                params = {'category': 'video','title': title,'url': url, 'desc': desc,'icon': icon,'good_for_fav': True}
                                self.addVideo(params)
                            else:
                                content_type = self.determineContentType(title, url)
                                if content_type == 'series':
                                    params = {'category': 'list_episodes','title': title,'url': url,'desc': desc,'icon': icon,'good_for_fav': True}
                                    self.addDir(params)
                                else:
                                    params = {'category': 'video','title': title,'desc': desc,'url': url,'icon': icon,'good_for_fav': True}
                                    self.addVideo(params)
                        if len(valid_items) >= 20:
                            last_item = valid_items[-1]
                            new_pick_up_id = str(last_item.get("ID", ""))
                            if new_pick_up_id and new_pick_up_id != pick_up_id:
                                params = dict(cItem)
                                params.update({'title': '\\c00FFFF00تحميل المزيد','pick_up_id': new_pick_up_id})
                                self.addDir(params)
                    else:
                        self.addDir({'category': 'list_items', 'title': 'لا توجد عناصر إضافية', 'url': ''})
                except Exception as e:
                    printDBG("Error parsing JSON: %s" % str(e))
                    printDBG("Response content: " + response_text)
                    self.addDir({'category': 'list_items', 'title': 'خطأ في تنسيق البيانات', 'url': ''})
            else:
                self.addDir({'category': 'list_items', 'title': 'استجابة فارغة من الخادم', 'url': ''})
        except Exception as e:
            printDBG("Error in load_more: %s" % str(e))
            self.addDir({'category': 'list_items', 'title': 'خطأ في تحميل المزيد', 'url': ''})
    def determineContentType(self, title, url=''):
        title_lower = title.lower()
        url_lower = url.lower() if url else ''
        printDBG(f"=== determineContentType DEBUG ===")
        printDBG(f"Title: {title}")
        printDBG(f"URL: {url}")
        printDBG(f"Title Lower: {title_lower}")
        printDBG(f"URL Lower: {url_lower}")
        episode_keywords = ['حلقة', 'الحلقة', 'episode', 'الحلقة الأخيرة', 'حلقة جديدة',]
        series_keywords = ['مسلسل', 'المسلسل', 'series', 'مسلسلات', 'المسلسلات','season', 'موسم', 'الموسم', 'سلسلة', 'برنامج']
        movie_keywords = ['فيلم', 'الفيلم', 'movie', 'film', 'أفلام', 'الأفلام', 'أغنية', 'اغنية', 'أغاني', 'اغاني','كليب', 'كلب', 'تصميم', 'تصاميم', 'مقطع', 'مقاطع']
        if any(keyword in url_lower for keyword in ['/اغاني/', '/أغاني/', '/music/', '/songs/', '/تصاميم-', '/design/']):
            result = 'movie'
            printDBG(f"Music/Design section detected: {result}")
            return result
        if any(keyword in title_lower for keyword in ['أغنية', 'اغنية', 'أغاني', 'اغاني', 'music', 'كليب', 'كلب', 'تصميم', 'تصاميم']):
            result = 'movie'
            printDBG(f"Music/Design title detected: {result}")
            return result
        for keyword in episode_keywords:
            if keyword in title_lower:
                result = 'episode'
                printDBG(f"Episode keyword '{keyword}' detected: {result}")
                return result
        for keyword in series_keywords:
            if keyword in title_lower:
                result = 'series'
                printDBG(f"Series keyword '{keyword}' detected: {result}")
                return result
        for keyword in movie_keywords:
            if keyword in title_lower:
                result = 'movie'
                printDBG(f"Movie keyword '{keyword}' detected: {result}")
                return result
        if re.search(r'(season|موسم|s)\s*\d+', title_lower):
            result = 'series'
            printDBG(f"Season pattern detected: {result}")
            return result
        if any(keyword in url_lower for keyword in ['/series/', '/مسلسلات/', '/مسلسل/', '/seasons/']):
            result = 'series'
            printDBG(f"Series URL pattern detected: {result}")
            return result
        if any(keyword in url_lower for keyword in ['/movies/', '/أفلام/', '/فيلم/', '/film/']):
            result = 'movie'
            printDBG(f"Movie URL pattern detected: {result}")
            return result
        if any(keyword in url_lower for keyword in [
            '/category/مسلسلات-اجنبية',
            '/category/',
            '/series-',
            '/مسلسل-'
        ]) and not any(keyword in url_lower for keyword in ['/افلام/', '/movies/', '/أغاني/', '/music/']):
            result = 'series'
            printDBG(f"Foreign series section detected: {result}")
            return result
        if '/أفلام' in url_lower or '/movies' in url_lower:
            result = 'movie'
            printDBG(f"Movies section detected: {result}")
            return result
        result = 'movie'
        printDBG(f"Default result: {result}")
        return result
    def extractDescFromNewly(self, html_block):
        desc_parts = []
        type_match = re.search(r'NewlyRibbon">([^<]+)</div>', html_block)
        if type_match:
            desc_parts.append('\\c00????00النوع: \\c00????FF' + type_match.group(1).strip())
        time_match = re.search(r'NewlyTimeAgo[^>]*>([^<]+)</div>', html_block)
        if time_match:
            desc_parts.append('\\c00????00وقت النشر: \\c00????FF' + time_match.group(1).strip())
        episode_match = re.search(r'NewlyEpNumber[^>]*>.*?(\d+)</div>', html_block)
        if episode_match:
            desc_parts.append('\\c00????00الحلقة: \\c00????FF' + episode_match.group(1).strip())
        return '\n'.join(desc_parts) if desc_parts else '\\c00????00محتوى مضاف حديثاً'
    def getLinksForVideo(self, cItem):
        printDBG("Lodynet.getLinksForVideo [%s]" % cItem)
        url = cItem.get('url', '')
        sts, data = self.getPage(url)
        if not sts:
            return []
        links = []
        referer = url
        servers = re.findall(r"SwitchServer\(this,\s*'([^']+)'\).*?>([^<]+)<", data)
        if servers:
            for srv_url, srv_name in servers:
                srv_url = self.getFullUrl(srv_url)
                srv_name = srv_name.strip()
                links.append({'name': srv_name,'url': srv_url,'need_resolve': 1,'Referer': referer})
                printDBG(" >> New server: %s (%s)" % (srv_name, srv_url))
        else:
            old_servers = re.findall(r'<li[^>]+data-embed=["\']([^"\']+)["\'][^>]*>([^<]+)<', data)
            for srv_url, srv_name in old_servers:
                srv_url = self.getFullUrl(srv_url)
                srv_name = srv_name.strip()
                links.append({'name': srv_name,'url': srv_url,'need_resolve': 1,'Referer': referer})
                printDBG(" >> Old server: %s (%s)" % (srv_name, srv_url))
        if not links:
            printDBG("Lodynet: لم يتم العثور على أي روابط سيرفر.")
            links.append({'name': 'الرابط الرئيسي','url': url,'need_resolve': 1,'Referer': referer})
        printDBG("Found %d links" % len(links))
        return links
    def getVideoLinks(self, videoUrl):
        printDBG("Lodynet.getVideoLinks [%s]" % videoUrl)
        if any(x in videoUrl for x in ['vidlo.us', 'viidshar.com', 'govad.xyz', 'vadbam.net']):
            return self.getVidloDirectLinks(videoUrl)
        if videoUrl.endswith('.mp4'):
            return [{'name': 'Direct MP4', 'url': videoUrl}]
        headers = {'User-Agent': self.USER_AGENT, 'Referer': 'https://lodynet.watch/'}
        url_with_meta = strwithmeta(videoUrl, headers)  # 🔥 استخدام videoUrl الكامل
        return self.up.getVideoLinkExt(url_with_meta)
    def listSearchResult(self, cItem, searchPattern, searchType):
        printDBG("Lodynet.listSearchResult [%s]" % searchPattern)
        if not searchPattern:
            return
        search_url = self.MAIN_URL + '/wp-content/themes/Lodynet2020/Api/RequestSearch.php?value=' + quote_plus(searchPattern)
        printDBG("Search URL: %s" % search_url)
        headers = {'User-Agent': self.USER_AGENT,'X-Requested-With': 'XMLHttpRequest','Referer': self.MAIN_URL,'Accept': 'application/json, text/javascript, */*; q=0.01'}
        try:
            import requests
            response = requests.get(search_url, headers=headers, timeout=30)
            response_text = response.text
            printDBG("Search API Response: %s" % response_text)
            if response_text and response_text.strip():
                try:
                    data = json.loads(response_text)
                    if isinstance(data, list) and len(data) >= 2:
                        search_results = data[1]
                        if isinstance(search_results, list) and search_results:
                            printDBG("تم العثور على %d نتيجة بحث" % len(search_results))
                            for item in search_results:
                                if not isinstance(item, dict):
                                    continue
                                title = item.get("Title", "")
                                item_url = item.get("Url", "")
                                category = item.get("Category", "")
                                cover = item.get("Cover", "")
                                if not title or not item_url:
                                    continue
                                try:
                                    if '\\u' in title:
                                        title = title.encode('utf-8').decode('unicode_escape')
                                    elif '&#x' in title:
                                        import html
                                        title = html.unescape(title)
                                except:
                                    pass
                                if item_url.startswith('http'):
                                    full_url = item_url
                                else:
                                    try:
                                        decoded_url = urllib.parse.unquote(item_url)
                                        if decoded_url.startswith('/'):
                                            full_url = self.MAIN_URL + decoded_url
                                        else:
                                            full_url = self.MAIN_URL + '/' + decoded_url
                                    except:
                                        full_url = self.MAIN_URL + '/' + item_url
                                icon = self.DEFAULT_ICON_URL
                                if cover:
                                    try:
                                        if '\\/' in cover:
                                            cover = cover.replace('\\/', '/')
                                        icon = self.getFullUrl(cover)
                                    except:
                                        icon = self.DEFAULT_ICON_URL
                                desc_parts = []
                                if category:
                                    desc_parts.append('\\c00????00القسم: \\c00????FF' + category)
                                desc = '\n'.join(desc_parts) if desc_parts else 'نتيجة بحث'
                                content_type = self.determineContentType(title, full_url)
                                if content_type == 'series':
                                    params = {'category': 'list_episodes','title': title.strip(),'url': full_url,'desc': desc,'icon': icon,'good_for_fav': True}
                                    self.addDir(params)
                                else:
                                    params = {'category': 'video','title': title.strip(),'url': full_url,'desc': desc,'icon': icon,'good_for_fav': True}
                                    self.addVideo(params)
                        else:
                            self.addDir({'category': 'search','title': '\\c00FF0000لم يتم العثور على نتائج','url': '','desc': 'لم يتم العثور على أي نتائج للبحث: ' + searchPattern})
                    else:
                        self.addDir({'category': 'search', 'title': '\\c00FF0000خطأ في تنسيق البيانات','url': '','desc': 'استجابة غير متوقعة من خادم البحث'})
                except Exception as e:
                    printDBG("Error parsing search JSON: %s" % str(e))
                    printDBG("Raw response: " + response_text)
                    self.addDir({'category': 'search','title': '\\c00FF0000خطأ في تحليل النتائج','url': '','desc': 'تعذر تحليل نتائج البحث: ' + str(e)})
            else:
                self.addDir({'category': 'search','title': '\\c00FF0000استجابة فارغة من الخادم', 'url': '','desc': 'لم يستجب خادم البحث للطلب'})
        except Exception as e:
            printDBG("Error in search: %s" % str(e))
            self.addDir({'category': 'search','title': '\\c00FF0000خطأ في البحث','url': '','desc': 'حدث خطأ أثناء البحث: ' + str(e)})
    def getArticleContent(self, cItem):
        printDBG("Lodynet.getArticleContent [%s]" % cItem)
        retTab = []
        url = cItem.get('url', '')
        sts, data = self.getPage(url)
        if not sts:
            return []
        title = cItem.get('title', '')
        icon = cItem.get('icon', self.DEFAULT_ICON_URL)
        desc = cItem.get('desc', '')
        desc_match = re.search(r'<div class="BoxContentInner">(.*?)</div>', data, re.S)
        if desc_match:
            desc = ph.clean_html(desc_match.group(1))
        if title:
            retTab.append({'title': title,'text': desc,'images': [{'title': '', 'url': icon}],'other_info': {}})
        return retTab
    def getVidloDirectLinks(self, baseUrl):
        printDBG('getVidloDirectLinks baseUrl[%s]' % baseUrl)
        COOKIE_FILE = GetCookieDir('vidlo.cookie')
        HTTP_HEADER = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0',
            'Referer': baseUrl
        }
        params = {'header': HTTP_HEADER, 'use_cookie': True, 'save_cookie': True, 'load_cookie': True, 'cookiefile': COOKIE_FILE, 'return_data': True,'follow_redirects': True}
        sts, data = self.cm.getPage(baseUrl, params)
        if not sts:
            printDBG('فشل تحميل الصفحة')
            return []
        final_url = self.cm.meta.get('url', baseUrl)
        printDBG('الرابط النهائي: %s' % final_url)
        video_urls = []
        if detect(data):
            try:
                unpacked = unpack(data)
                if unpacked:
                    printDBG('فك التشفير نجح باستخدام jsunpack')
                    data = unpacked + data  # إضافة البيانات المفكوكة للبيانات الأصلية
            except Exception as e:
                printDBG('فشل فك التشفير باستخدام jsunpack: %s' % str(e))
        packed_data = get_packed_data(data)
        if packed_data:
            printDBG('تم العثور على بيانات مضغوطة باستخدام get_packed_data')
            data += packed_data
        sources_match = re.search(r'sources\s*:\s*\[([^\]]+)\]', data)
        if sources_match:
            sources_content = sources_match.group(1)
            printDBG('تم العثور على مصادر الفيديو')
            video_objects = re.findall(r'\{[^{}]*\}', sources_content)
            for obj in video_objects:
                url_match = re.search(r'file["\']?\s*:\s*["\'](https?://[^"\']+)["\']', obj)
                label_match = re.search(r'label["\']?\s*:\s*["\']([^"\']+)["\']', obj)
                if url_match:
                    video_url = url_match.group(1)
                    if label_match:
                        label = label_match.group(1)
                        if '720' in label or 'hd' in label.lower():
                            label = 'HD [720p]'
                        elif '480' in label or 'sd' in label.lower():
                            label = 'SD [480p]'
                        elif '360' in label or 'low' in label.lower():
                            label = 'LOW [360p]'
                    else:
                        if '720p' in video_url.lower() or '/hd/' in video_url.lower():
                            label = 'HD [720p]'
                        elif '1080p' in video_url.lower() or '/fullhd/' in video_url.lower():
                            label = 'FULL HD [1080p]' 
                        elif '480p' in video_url.lower() or '/sd/' in video_url.lower():
                            label = 'SD [480p]'
                        elif '360p' in video_url.lower() or '/low/' in video_url.lower():
                            label = 'LOW [360p]'
                        else:
                            label = 'direct'
                    if video_url not in [v['url'] for v in video_urls]:
                        video_urls.append({'url': video_url, 'label': label})
                        printDBG('تم استخراج: %s [%s]' % (video_url, label))
        if not video_urls:
            printDBG('البحث عن روابط MP4 مباشرة')
            quality_patterns = [
                (r'https?://[^\s"\']+?720p[^\s"\']*\.mp4', 'HD [720p]'),
                (r'https?://[^\s"\']+?1080p[^\s"\']*\.mp4', 'FULL HD [1080p]'),
                (r'https?://[^\s"\']+?480p[^\s"\']*\.mp4', 'SD [480p]'),
                (r'https?://[^\s"\']+?360p[^\s"\']*\.mp4', 'LOW [360p]'),
                (r'https?://[^\s"\']+?\.mp4[^\s"\']*', 'direct')
            ]
            for pattern, quality in quality_patterns:
                matches = re.findall(pattern, data)
                for url in matches:
                    if url not in [v['url'] for v in video_urls]:
                        video_urls.append({'url': url, 'label': quality})
                        printDBG('تم العثور على MP4: %s [%s]' % (url, quality))
        vadbam_domains = ['vadbam.net', 'vdbtm.shop']  # 🔥 تحديث النطاقات
        if not video_urls and any(domain in final_url for domain in vadbam_domains):
            printDBG('البحث عن رابط vadbam المحدد')
            token_patterns = [
                r'6jmnwdooziazsalrixwal4fsijsegohjlt2yfv5hhhb2er4ixuc[a-z0-9]+',
                r'[a-z0-9]{50,}'
            ]
            vadbam_token = None
            for pattern in token_patterns:
                token_match = re.search(pattern, data)
                if token_match:
                    vadbam_token = token_match.group(0)
                    printDBG('تم العثور على توكن vadbam: %s' % vadbam_token)
                    break
            if vadbam_token:
                vadbam_url = 'https://n64no-02.times20qu20.shop/' + vadbam_token + '/v.mp4'
                video_urls.append({'url': vadbam_url, 'label': 'HD [720p]'})
                printDBG('تم بناء رابط vadbam: %s' % vadbam_url)
            else:
                vadbam_patterns = [
                    r'https?://n64no-02\.times20qu20\.shop/[^/"\']+?/v\.mp4',
                    r'https?://[a-z0-9\-]+\.times20qu20\.shop/[^/"\']+?/v\.mp4'
                ]
                for pattern in vadbam_patterns:
                    vadbam_match = re.search(pattern, data)
                    if vadbam_match:
                        video_urls.append({'url': vadbam_match.group(0), 'label': 'HD [720p]'})
                        printDBG('تم العثور على رابط vadbam مباشرة: %s' % vadbam_match.group(0))
                        break
        govad_domains = ['govad.xyz', 'goveed1.space']
        if not video_urls and any(domain in final_url for domain in govad_domains):
            printDBG('البحث عن رابط govad المحدد')
            token_patterns = [
                r'to3qvsqfkjvsy46b3v6wxj5miprsdgtglca2uskke2wsfieaih2[a-z0-9]+',
                r'[a-z0-9]{50,}'
            ]
            govad_token = None
            for pattern in token_patterns:
                token_match = re.search(pattern, data)
                if token_match:
                    govad_token = token_match.group(0)
                    printDBG('تم العثور على توكن govad: %s' % govad_token)
                    break
            if govad_token:
                govad_url = 'https://wsxcvx6.zfghrew10.shop/' + govad_token + '/v.mp4'
                video_urls.append({'url': govad_url, 'label': 'HD [720p]'})
                printDBG('تم بناء رابط govad: %s' % govad_url)
            else:
                govad_patterns = [
                    r'https?://wsxcvx6\.zfghrew10\.shop/[^/"\']+?/v\.mp4',
                    r'https?://[a-z0-9\-]+\.zfghrew10\.shop/[^/"\']+?/v\.mp4'
                ]
                for pattern in govad_patterns:
                    govad_match = re.search(pattern, data)
                    if govad_match:
                        video_urls.append({'url': govad_match.group(0), 'label': 'HD [720p]'})
                        printDBG('تم العثور على رابط govad مباشرة: %s' % govad_match.group(0))
                        break
        if not video_urls and 'vidlo.us' in final_url:
            printDBG('البحث عن روابط vidlo مع الجودات')
            vidlo_patterns = [
                r'https?://[a-z0-9]+\.vidlo\.us/[a-z0-9]+/v\.mp4',
                r'https?://vidlo\.us/[a-z0-9]+/v\.mp4'
            ]
            vidlo_links_found = []
            for pattern in vidlo_patterns:
                matches = re.findall(pattern, data)
                for url in matches:
                    if url not in vidlo_links_found:
                        vidlo_links_found.append(url)
            if vidlo_links_found:
                vidlo_links_found.sort(key=len)
                quality_labels = ['HD [720p]', 'SD [480p]', 'LOW [360p]']
                for i, url in enumerate(vidlo_links_found):
                    if i < len(quality_labels):
                        label = quality_labels[i]
                    else:
                        label = f'Quality {i+1}'
                    if url not in [v['url'] for v in video_urls]:
                        video_urls.append({'url': url, 'label': label})
                        printDBG('تم العثور على رابط vidlo: %s [%s]' % (url, label))
        if not video_urls:
            printDBG('البحث عن روابط مباشرة في HTML')
            direct_patterns = [
                r'src\s*=\s*["\'](https?://[^"\']+?\.mp4[^"\']*)["\']',
                r'file["\']?\s*=\s*["\'](https?://[^"\']+?\.mp4[^"\']*)["\']',
                r'(https?://[^\s"\'<>]+\.mp4[^"\'<>]*)'
            ]
            direct_links_found = []
            for pattern in direct_patterns:
                matches = re.findall(pattern, data)
                for match in matches:
                    if (match.startswith('http') and 
                        'adblocktape.wiki' not in match and 
                        match not in direct_links_found):
                        direct_links_found.append(match)
            if direct_links_found:
                quality_order = ['720p', '1080p', '480p', '360p', 'hd', 'sd', 'low']
                direct_links_found.sort(key=lambda x: any(q in x.lower() for q in quality_order), reverse=True)
                for i, url in enumerate(direct_links_found):
                    if '720p' in url.lower() or 'hd' in url.lower():
                        label = 'HD [720p]'
                    elif '480p' in url.lower() or 'sd' in url.lower():
                        label = 'SD [480p]'
                    elif '360p' in url.lower() or 'low' in url.lower():
                        label = 'LOW [360p]'
                    elif '1080p' in url.lower() or 'fullhd' in url.lower():
                        label = 'FULL HD [1080p]'
                    else:
                        if i == 0:
                            label = 'HD [720p]'
                        elif i == 1:
                            label = 'SD [480p]'
                        elif i == 2:
                            label = 'LOW [360p]'
                        else:
                            label = f'Quality {i+1}'
                    if url not in [v['url'] for v in video_urls]:
                        video_urls.append({'url': url, 'label': label})
                        printDBG('تم العثور على رابط في HTML: %s [%s]' % (url, label))
        if video_urls:
            quality_priority = {'FULL HD [1080p]': 0,'HD [720p]': 1, 'SD [480p]': 2,'LOW [360p]': 3}
            def get_quality_priority(item):
                label = item['label']
                return quality_priority.get(label, 999)
            video_urls.sort(key=get_quality_priority)
            result = []
            for item in video_urls:
                result.append({
                    'name': item['label'],
                    'url': strwithmeta(item['url'], {
                        'Referer': final_url,
                        'User-Agent': HTTP_HEADER['User-Agent']
                    })
                })
            printDBG('تم العثور على %d رابط' % len(result))
            for item in result:
                printDBG('   - %s: %s' % (item['name'], item['url']))
            return result
        printDBG('لم يتم العثور على أي رابط فيديو')
        return []
    def handleService(self, index, refresh=0, searchPattern='', searchType=''):
        printDBG('Lodynet.handleService start')
        CBaseHostClass.handleService(self, index, refresh, searchPattern, searchType)
        name = self.currItem.get("name", '')
        category = self.currItem.get("category", '')
        printDBG("handleService: || name[%s], category[%s]" % (name, category))
        self.currList = []
        if name is None:
            self.listMainMenu({'name': 'category'})
        elif category == 'sub_menu':
            self.listSubMenu(self.currItem)
        elif category == 'list_items':
            self.listItems(self.currItem)
        elif category == 'list_episodes':
            self.listEpisodes(self.currItem)
        elif category == 'load_more':
            self.loadMore(self.currItem)
        elif category == 'load_more_episodes':
            self.loadMore(self.currItem)
        elif category == 'search':
            self.listSearchResult(self.currItem, searchPattern, searchType)
        elif category == 'search_history':
            self.listsHistory({'category': 'search', 'name': 'history'})
        elif category == 'delete_history':
            self.delHistory(self.sessionEx)
    def listsHistory(self, baseItem={'name': 'history', 'category': 'search'}, desc_key='plot', desc_base=("النوع: ")):
        list = self.history.getHistoryList()
        for histItem in list:
            plot = ''
            try:
                if type(histItem) is type({}):
                    pattern = histItem.get('pattern', '')
                    search_type = histItem.get('type', '')
                    if '' != search_type:
                        plot = desc_base + search_type
                else:
                    pattern = histItem
                    search_type = None
                params = dict(baseItem)
                params.update({'title': pattern, 'search_type': search_type, desc_key: plot})
                self.addDir(params)
            except Exception:
                printExc()
    def start(self, cItem):
        return self.handleService(cItem)
class IPTVHost(CHostBase):
    def __init__(self):
        CHostBase.__init__(self, Lodynet(), True, [])
    def withArticleContent(self, cItem):
        if 'video' == cItem.get('type', '') or 'list_episodes' == cItem.get('category', ''):
            return True
        return False
###################################################################### الحمد لله