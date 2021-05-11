

import sys, requests, io, pickle
from PIL import Image


# Utils Class
#
#
class ClientUtils:
    
    @classmethod
    def getData(self, url, func, log=None, status=None, return_type="text"):
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                if status is not None:
                    status.info("Downloading from url: " + url)
                if return_type=="text":
                    return func(res.text) 
                if return_type=="content":
                    return func(res.content)
                if return_type=="response":
                    return func(res)
                return res
        except requests.exceptions.Timeout:
            if status is not None:
                status.err("Error " + url + " : Timeout")    
            return None

    
    ##################
    # private methods:
    ##################
    @classmethod
    def __resizeImageWidth(cls, img, width):
        wpercent = (width/float(img.size[0]))
        hsize = int((float(img.size[1])*float(wpercent)))
        return img.resize((width,hsize), Image.ANTIALIAS)

    @classmethod
    def __resizeImageHeight(cls, img, height):
        hpercent = (height/float(img.size[1]))
        wsize = int((float(img.size[0]*float(hpercent))))
        return img.resize((wsize, height), Image.ANTIALIAS)


    #######################
    # Image Manipulation
    #######################
    # keep aspect ratio same on resizing downloaded data.
    @classmethod
    def resizeImageKeepingAspectRatio(cls, img_data, limit_width, limit_height=None):
        img = Image.open(img_data)
        w = img.size[0]
        h = img.size[1]
        if w > limit_width:
            img = cls.__resizeImageWidth(img, limit_width)
            bio = io.BytesIO()
            img.save(bio, format="PNG")
            return bio.getvalue()
        else:
            if limit_height != None:
                if h > limit_height:
                    img = cls.__resizeImageHeight(img, limit_height)
                    bio = io.BytesIO()
                    img.save(bio, format="PNG")
                    return bio.getvalue()
        return img_data.getvalue()


    @classmethod
    def doNothing(cls, param):
        return param

    @classmethod
    def loadImageUrl(cls, url, url_cache=None):
        if url_cache:
            if url in url_cache.keys():
                return url_cache[url]
            else:
                data = cls.getData(url, cls.doNothing, return_type="response")
                url_cache[url] = data
                return data
        else:
            data = cls.getData(url, cls.doNothing, return_type="response")
            return data


    #################
    # pickling object
    #################
    @classmethod
    def objToFile(cls, obj, filename):
        dbfile = open(filename, 'wb')    
        pickle.dump(obj, dbfile)                     
        dbfile.close()

    @classmethod
    def fileToObj(cls, filename):
        dbfile = open(filename, 'rb')     
        db = pickle.load(dbfile)
        dbfile.close()
        return db


    