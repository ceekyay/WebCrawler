import scrapy
import re
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from spiderman.items import SpidermanItem
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError, TCPTimedOutError

finishedPages = set()


class crawlee(CrawlSpider):
    name = "uiowa"
    allowed_domains = ["uiowa.edu"]
    start_urls = ["https://uiowa.edu"]

    # rule = [Rule(LinkExtractor(allow=r"uiowa.edu/"), callback='parse_links')]
    # Because the above callback calls an in-built version of parse() instead of this one.
    # rule = [Rule(LinkExtractor(allow=r"uiowa.edu/"), callback='parse')]



    def parse(self, response):
        linksCrawled = []
        extensions = ['.pdf', '.bat', '.gif', '.jpg', '.png', '.cfm', '.ics']
        blockedChars = ['/', '#']
        # linkCheckExp = "^(?:http|https):\/\/(?:[\w\.\-\+])+(?:$|\/+[\w\~\+\-])"
        linkCheckExp = "^(?:http|https):\/\/(?:[\w\.\-\+])+(?:$|\/)"
        validLink = re.compile(linkCheckExp)
        links = response.xpath("//a/@href").extract()

        # print("RESPONSE URL: ", response.url)
        # print("LINKS: ", links)
        # temp = response.url+links[1]
        # print("FIXED URL: ", temp)

        if "www." in response.url[8:12]:
            response.url = response.url[:8] + response.url[12:]

        for i in range(len(links)):

            # Some webpages have weird spacings ex:"\r\n\ https://cs.uiowa.edu"
            # This will remove them all.

            links[i] = links[i].strip()
            # print("RES-URL: ", response.url)
            # print("OG-LINK: ", links[i])
            # Since some of the links are relative paths, ex:"/resources/contact"
            # Fix them by making them absolute paths
            if not links[i].startswith("https"):
                # Check if it started with "http"
                # If true, then add "s"
                if links[i].startswith("http"):
                    temp = links[i]
                    links[i] = temp[:4] + "s" + temp[4:]
                    # print("FIXED HTTPS: ", links[i])
                elif "mailto" not in links[i][:6]:
                    # links[i] = response.url + links[i]
                    temp = response.url
                    temp2 = links[i]
                    ref = len(temp) - 1
                    sz = len(temp2)
                    # Some links start with "wwww"
                    if links[i].startswith("www"):
                        links[i] = 'https://' + links[i]

                    elif links[i].startswith("//www"):
                        links[i] = 'https:' + links[i]

                    # Some response.url could be ex: "cs.uiowa.edu/" and
                    # links[i] could be "/resources/contact"
                    # And we need it to be "cs.uiowa/edu/resources/contact"

                    # Here I am trying to look for uiowa.edu or uiowa.edu/ or uiowa.edu/something
                    # CONDITION-1

                    elif temp[len(temp) - 9:] == "uiowa.edu" and temp2[0] == "/":
                        links[i] = temp + temp2
                        # print("CONDITION-1: ", links[i])

                    # CONDITION-2
                    elif temp[len(temp) - 9:] == "uiowa.edu" and temp2[0] not in blockedChars:
                        links[i] = temp + "/" + temp2
                        # print("CONDITION-2: ", links[i])

                    # CONDITION-3
                    elif temp[len(temp) - 10:] == "uiowa.edu/" and temp2[0] == "/":
                        links[i] = temp + temp2[1:]
                        # print("CONDITION-3: ", links[i])

                    # This is for filtering out anchors on a page. I'm
                    # turning this into an invalid link, so it will omitted
                    # in the later stages.

                    # CONDITION-4
                    elif temp[len(temp) - 10:] == "uiowa.edu/" and temp2[0] == "#":
                        links[i] = temp[:len(temp) - 1] + temp2
                        # print("CONDITION-4: ", links[i])

                    # CONDITION-5
                    elif "uiowa.edu/" in temp and temp2[0] == "/":
                        k = temp.find("uiowa.edu")
                        k = k + 9
                        links[i] = temp[:k] + temp2
                        # print("RES-URL: ", temp)
                        # print("TEMP[:20]: ", temp[:20])
                        # print("CONDITION-5: ", links[i])

                    # CONDITION-6
                    elif "uiowa.edu/" in temp and temp2[0] == "#":
                        k = temp.find("uiowa.edu")
                        k = k + 9
                        links[i] = temp[:k] + temp2
                        # print("CONDITION-6: ", links[i])

                    # CONDITION-7
                    # Checking if the link is a .html
                    elif "uiowa.edu/" in temp and temp2[sz - 5:] == ".html":
                        # Only stuff after the last "/" has to change
                        k = temp.rfind("/")
                        # k = -1 will never occur
                        links[i] = temp[:k + 1] + temp2
                        # print("CONDITION-7: ", links[i])

                    # We already know it's not .html
                    # CONDITION-8
                    elif "uiowa.edu/" in temp and temp2[0] not in blockedChars:
                        # We will invalidate only extensions with 4 spaces.
                        # Ex: .pdf, .gif, .jpg, .png, .bat
                        if temp2[sz - 4:] in extensions:
                            links[i] = ''
                            # print("CONDITION-8a: ", links[i])
                        else:
                            # There is no chance of response.url having "/" at the
                            # end of it's URL, because each link is cleaned further
                            # down, before being added into the array
                            k = temp.rfind("/")
                            links[i] = temp[:k + 1] + temp2
                            # print("CONDITION-8b: ", links[i])



                    # CONDITION-9
                    else:
                        links[i] = response.url + links[i]
                        # print("CONDITION-9: ", links[i])

                        # print("Cleaned Links-1: ", links[i])
                        # if temp[ref] == (temp2[0]):
                        # links[i] = temp[:ref] + links[i]
                        # elif temp[ref] != "/" and temp2[0] not in blockedChars:
                        # links[i] = response.url + '/' + links[i]
                        # else:
                        # links[i] = response.url + links[i]

            # Fix the links redirected from footers. Cuz they tend
            # to have a different URL from the real one & go on a loop.
            # Edit links with "?" in them. ex: cs.uiowa.edu/c.php? becomes
            # cs.uiowa.edu/

            if "?" in links[i]:
                k = links[i].find("?")
                newCp = links[i][k:]
                # n == -1 if ex: "cs.uiowa.edu/c.php?"
                n = newCp.find("/")
                # Make sure to deal with n == -1, incase no "/" found
                # Everything from "?" till it's previous "/" should be erased.
                end = links[i][:k].rfind("/")
                if n == -1:

                    links[i] = links[i][:end]

                else:
                    links[i] = links[i][:end] + newCp[n:]

            # print("UTM_SRC-CLEAN: ", links[i])

            # Remove the link if javascript is found
            if "javascript:" in links[i]:
                links[i] = ''

            # Remove if links is a telephone num

            if "tel:" in links[i]:
                links[i] = ''

            # Setting a limit to the size of link, because extremely long one's
            # often dont work. See the README file for such an example and why I
            # choose this number

            if "../" in links[i]:
                links[i] = ''

            if "./" in links[i]:
                links[i] = ''

            if "apidocs/" in links[i]:
                links[i] = ''

            nodeTest = links[i].find("uiowa.edu/")
            nodeCp = links[i][nodeTest + 10:]
            check1 = nodeCp.find("/")
            if check1 != -1:
                string1 = nodeCp[:check1]
                lenStr = len(string1)
                totalLen = check1 + 1 + lenStr + 1
                if len(nodeCp) >= totalLen:
                    if string1 in nodeCp[check1 + 1:lenStr + 1]:
                        links[i] = ''



                        # string2 = [nodeCp+1:nodeCp+lenStr]

            if "calendar/" in links[i]:
                links[i] = ''

            if "calendar.ics" in links[i]:
                links[i] = ''

            if "ical/" in links[i]:
                links[i] = ''

            if len(links[i]) > 200:
                links[i] = ''

            if "cnm/" in links[i]:
                first = links[i].find("cnm/")
                last = links[i].rfind("cnm/")
                if first != last:
                    links[i] = links[i][:first + 4] + linksp[i][last + 3:]

            if "events/" in links[i]:
                links[i] = ''

            if "ap-purchasing/" in links[i]:
                first = links[i].find("ap-purchasing/")
                last = links[i].rfind("ap-purchasing/")
                if first != last:
                    links[i] = links[i][:first + 14] + links[i][last + 13:]

            if "label/REDCapDocs/" in links[i]:
                first = links[i].find("label/REDCapDocs/")
                links[i] = links[i][:first]
            # Another problem is that "www.cs.uiowa.edu" and "cs.uiowa.edu" are same
            # but the program see's it differently. Also same applies to links with
            # "/" in the ending.

            if "book.grad.uiowa.edu/events" in links[i]:
                links[i] = ''

            if "confluence/" in links[i]:
                links[i] = ''

            if "MagEphem/" in links[i]:
                links[i] = ''

            if "@uiowa.edu" in links[i]:
                links[i] = ''

            if "www." in links[i][8:12]:
                links[i] = links[i][:8] + links[i][12:]

            links[i] = re.sub(r'\d{4}-\d{2}-\d{2}', '', links[i])
            links[i] = re.sub(r'\d{4}\/\d{2}\/\d{2}', '', links[i])

            if "//" in links[i][8:]:
                links[i] = ''

            if "Flight/RBSP" in links[i]:
                links[i] = ''

            if "diyhistory.lib.uiowa.edu/items/show/" in links[i]:
                links[i] = ''

            if "diyhistory.lib.uiowa.edu/collections/show/" in links[i]:
                links[i] = ''

            linkLen = len(links[i]) - 1
            temp = links[i]
            if linkLen > 0 and temp[linkLen] == "/":
                links[i] = temp[:linkLen]

            # completely omit these links
            if 'search.lib.uiowa.edu' in links[i][8:]:
                links[i] = ''

            elif 'international.uiowa.edu/news/' in links[i][8:]:
                links[i] = ''

            elif 'guides.lib.uiowa.edu' in links[i][8:]:
                links[i] = ''

            # Crawled this site after finish everything seperately. It is a weird
            # old site. No standard req's are met and goes on a infinite loop
            elif 'continuetolearn.uiowa.edu' in links[i]:
                links[i] = ''

            # print("Final-Clean-Links: ", links[i])

            if validLink.match(links[i]) and links[i] not in linksCrawled:

                # print("LINK: ", links[i])
                linksCrawled.append(links[i])
                crawlData = {'Links': links[i], 'URL': response.url}

                global finishedPages
                if not response.url in finishedPages:
                    finishedPages.add(response.url)

                yield crawlData

                url = str(links[i])
                if not url in finishedPages:
                    yield Request(url, callback=self.parse, errback=self.errback_httpbin)


    def errback_httpbin(self, failure):
        # log the failures
        self.logger.error(repr(failure))


        if failure.check(HttpError):
           response = failure.value.response
           self.logger.error('HttpError on %s', response.url)


        elif failure.check(DNSLookupError):
           request = failure.request
           self.logger.error('DNSLookupError on %s', request.url)


        elif failure.check(TimeoutError):
           request = failure.request
           self.logger.error('TimeoutError on %s', request.url)





















