# - * - coding: utf-8 -*-#
from __future__ import absolute_import, division, unicode_literals

import re
import urlparse
import json
import requests
import string
from scrapy import Request
from HP_Master_Project.utils import extract_first, clean_text, clean_list
from HP_Master_Project.items import ProductItem
from HP_Master_Project.spiders import BaseProductsSpider, FormatterWithDefaults


class CdwSpider(BaseProductsSpider):
    name = "cdw_products"
    allowed_domains = ['cdw.com', 'www.cdw.com']

    SEARCH_URL = 'https://www.cdw.com/shop/search/result.aspx?key={search_term}&ctlgfilter=' \
                 '&searchscope=all&sr=1&pCurrent={page_num}&pPage=1'

    API_URL = 'https://admin.metalocator.com/webapi/api/matchedretailerproducturls?Itemid=8343' \
              '&apikey=f5e4337a05acceae50dc116d719a2875&username=fatica%2Bscrapingapi@gmail.com' \
              '&password=8y3$u2ehu2e..!!$$&retailer_id={retailer_id}'

    TOTAL_MATCHES = None

    RESULT_PER_PAGE = None

    def __init__(self, *args, **kwargs):
        super(CdwSpider, self).__init__(
            site_name=self.allowed_domains[0], *args, **kwargs)
        self.current_page = 1
        self.user_agent = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/60.0.3112.90 Safari/537.36")
        self.url_formatter = FormatterWithDefaults(page_num=1)

    def start_requests(self):
        for request in super(CdwSpider, self).start_requests():
            if not self.product_url:
                request = request.replace(callback=self.parse_search)
            yield request

    def parse_search(self, response):
        page_title = response.xpath('//div[@class="search-pagination"]').extract()
        if page_title or self.retailer_id:
            return self.parse(response)

        else:
            category_url = response.xpath('//div[@class="button-lockup -center"]/a/@href').extract()
            c_url = urlparse.urljoin(response.url, category_url[0])
            return Request(url=c_url, meta=response.meta, callback=self.parse_category_link)

    def parse_category_link(self, response):
        link = response.xpath('//div[@class="button-lockup -center"]/a/@href').extract()
        if link:
            link = urlparse.urljoin(response.url, link[0])
            yield Request(url=link, meta=response.meta, dont_filter=True, callback=self.parse_category_links)

    @staticmethod
    def parse_category_links(response):
        link = response.xpath('//div[contains(@class, "multi-button")]/div[@class="dropdown"]'
                              '/a/@href').extract()
        for l in link:
            if 'shop' in l:
                l = urlparse.urljoin(response.url, l)
                yield Request(url=l, meta=response.meta, dont_filter=True)

    def _parse_single_product(self, response):
        return self.parse_product(response)

    def parse_product(self, response):
        product = ProductItem()

        # Parse name
        name = self._parse_name(response)
        product['name'] = name

        # Parse brand
        brand = self._parse_brand(response)
        product['brand'] = brand

        # Parse image
        image = self._parse_image(response)
        product['image'] = image

        product['link'] = response.url

        # Parse model
        model = self._parse_model(response)
        product['model'] = model

        # Parse categories
        categories = self._parse_categories(response)
        product['categories'] = categories

        # Parse unspec
        unspec = self._parse_unspec(response)
        product['unspec'] = unspec

        # Parse currencycode
        product['currencycode'] = 'USD'

        # Set locale
        product['locale'] = 'en-US'

        # Parse price
        price = self._parse_price(response)
        product['price'] = price

        # Parse sale price
        product['saleprice'] = price

        # Parse in_store
        in_store = self._parse_instore(response)
        product['instore'] = in_store

        # Parse ship to store
        ship_to_store = self._parse_shiptostore(response)
        product['shiptostore'] = ship_to_store

        # Parse shipping phrase
        shipping_phrase = self._parse_shippingphrase(response)
        product['shippingphrase'] = shipping_phrase

        # Parse stock status
        stock_status = self._parse_stock_status(response)
        product['productstockstatus'] = stock_status

        # Parse gallery
        gallery = self._parse_gallery(response)
        product['gallery'] = gallery

        # Parse features

        features = self._parse_features(response)
        product['features'] = features

        # Parse condition
        product['condition'] = 1

        return product

    @staticmethod
    def _parse_name(response):
        name = response.xpath('//h1[@id="primaryProductName"]/span[@itemprop="name"]/text()').extract()
        if name:
            return name[0]

    @staticmethod
    def _parse_brand(response):
        brand = response.xpath('//span[@itemprop="brand"]/text()').extract()
        if not brand:
            brand = response.xpath('//span[@class="brand"]/text()').extract()
        return brand[0].strip() if brand else None

    @staticmethod
    def _parse_image(response):
        image_url = response.xpath('//div[@class="main-image"]/img[@itemprop="image"]'
                                   '/@data-blzsrc').extract()
        if image_url:
            image_url = 'https:' + image_url[0]
            return image_url

    @staticmethod
    def _parse_categories(response):
        categories = response.xpath('//div[@class="breadCrumbs"]//a[@itemprop="item"]/@title').extract()
        return categories

    @staticmethod
    def _parse_unspec(response):
        unspec = response.xpath('//span[@itemprop="gtin8"]/text()').extract()
        if unspec:
            return unspec[0]

    def _parse_gallery(self, response):
        image_list = []
        base_image_url = self._parse_image(response).replace("?$product-main$", "")
        gallery = base_image_url + '?$product_60$'
        image_list.append(gallery)
        alpha_num = string.ascii_lowercase

        for i in range(20):
            image_url = base_image_url + alpha_num[i] + '?$product_60$'
            res = requests.get(image_url, timeout=10)

            if len(res.content) == 933:
                break
            image_list.append(image_url)

        return image_list

    def _parse_model(self, response):
        model = extract_first(response.xpath('//span[@itemprop="mpn"]/text()'))
        return clean_text(self, model)

    @staticmethod
    def _parse_price(response):
        price = response.xpath('//span[@itemprop="price"]/text()').extract()
        if price:
            return float(price[0].replace(",", ""))

    def _parse_instore(self, response):
        if self._parse_price(response):
            return 1

        return 0

    def _parse_shiptostore(self, response):
        if self._parse_shippingphrase(response):
            return 1

        return 0

    @staticmethod
    def _parse_shippingphrase(response):
        shipping_phrase = response.xpath('//div[@class="long-message-block"]//text()').extract()
        return "".join(shipping_phrase).strip()

    @staticmethod
    def _parse_stock_status(response):
        stock_value = 4
        stock_status = response.xpath('//link[@itemprop="availability"]/@href').extract()
        if stock_status:
            stock_status = stock_status[0].lower()

        if 'outofstock' in stock_status:
            stock_value = 0

        if 'instock' in stock_status:
            stock_value = 1

        if 'callforavailability' in stock_status:
            stock_value = 2

        if 'discontinued' in stock_status:
            stock_value = 3

        return stock_value

    def _parse_features(self, response):
        features = []
        features_name = response.xpath('//ul[@id="productSpecsContainer"]'
                                       '/li//label[contains(@for, "product_spec")]/text()').extract()
        for f_name in features_name:
            f_content = response.xpath('//ul[@id="productSpecsContainer"]'
                                       '/li/div[contains(@id, "product_spec")]'
                                       '/*[@aria-label="%s"]'
                                       '//text()' % f_name).extract()
            f_content = clean_list(self, f_content)
            if len(f_content) > 1:
                f_content_title = response.xpath('//ul[@id="productSpecsContainer"]'
                                                 '/li/div[contains(@id, "product_spec")]'
                                                 '/*[@aria-label="%s"]'
                                                 '//span[@class="strong"]/text()' % f_name).extract()
                f_content_title = clean_list(self, f_content_title)

                f_content_text = response.xpath('//ul[@id="productSpecsContainer"]'
                                                '/li/div[contains(@id, "product_spec")]'
                                                '/*[@aria-label="%s"]'
                                                '//span[not(contains(@class,"strong"))]'
                                                '/text()' % f_name).extract()
                f_content_text = clean_list(self, f_content_text)

                for f_c_title in f_content_title:
                    index = f_content_title.index(f_c_title)
                    feature = {f_c_title.replace(":", ""): f_content_text[index]}
                    features.append(feature)

            else:
                f_content = f_content[0]
                f_content = clean_text(self, f_content)
                feature = {f_name: f_content}
                features.append(feature)

        return features

    def _scrape_total_matches(self, response):
        totals = re.search("'search_results_count':'(\d+)',", response.body)
        if totals:
            totals = totals.group(1).replace(',', '').replace('.', '').strip()
            if totals.isdigit():
                if not self.TOTAL_MATCHES:
                    self.TOTAL_MATCHES = int(totals)
                return int(totals)
        if self.retailer_id:
            data = json.loads(response.body)
            return len(data)

    def _scrape_results_per_page(self, response):
        if self.retailer_id:
            return None
        result_per_page = re.search('1 - (\d+)</strong>', response.body)
        if result_per_page:
            result_per_page = result_per_page.group(1).replace(',', '').replace('.', '').strip()
            if result_per_page.isdigit():
                if not self.RESULT_PER_PAGE:
                    self.RESULT_PER_PAGE = int(result_per_page)
                return int(result_per_page)

    def _scrape_product_links(self, response):
        links = response.xpath('//div[@class="search-results"]'
                               '/div[@class="search-result"]//a[@class="search-result-product-url"]/@href').extract()

        if not links:
            data = json.loads(response.body)
            link_list = data
            for link in link_list:
                link = link['product_link']
                links.append(link)

        for link in links:
            url = urlparse.urljoin(response.url, link)
            yield url, ProductItem()

    def _scrape_next_results_page_link(self, response):
        if self.retailer_id:
            return None
        page_count = self.TOTAL_MATCHES / self.RESULT_PER_PAGE + 1

        self.current_page += 1

        if self.current_page <= page_count:
            next_page = self.SEARCH_URL.format(page_num=self.current_page,
                                               search_term=response.meta['search_term'])
            return next_page
