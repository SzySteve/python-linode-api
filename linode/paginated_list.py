import math

class PaginatedList(object):
    def __init__(self, client, page_endpoint, page=[], max_pages=1,
            total_items=None, parent_id=None, filters=None):
        self.client = client
        self.page_endpoint = page_endpoint
        self.query_filters = filters
        self.page_size = len(page)
        self.max_pages = max_pages
        self.lists = [ None for i in range(0, self.max_pages) ]
        self.lists[0] = page
        self.list_cls = type(page[0]) if page else None # TODO if this is None that's bad
        self.objects_parent_id = parent_id
        self.cur = 0 # for being a generator

        self.total_items = total_items
        if not total_items:
            self.total_items = len(page)

    def first(self):
        return self[0]

    def last(self):
        return self[-1]

    def only(self):
        if len(self) == 1:
            return self[0]
        raise ValueError("List {} has more than one element!".format(self))

    def __repr__(self):
        return "PaginatedList ({} items)".format(self.total_items)

    def _load_page(self, page_number):
        j = self.client.get("/{}?page={}".format(self.page_endpoint, page_number+1),
                filters=self.query_filters)

        if j['pages'] != self.max_pages or j['results'] != len(self):
            raise RuntimeError('List {} has changed since creation!'.format(self))

        l = PaginatedList.make_list(j["data"], self.client, self.list_cls,
                parent_id=self.objects_parent_id)
        self.lists[page_number] = l

    def __getitem__(self, index):
        # this comes in here now, but we're hadling it elsewhere
        if isinstance(index, slice):
            return self._get_slice(index)

        # handle negative indexing
        if index < 0:
            index = len(self) + index
            if index < 0:
                raise IndexError('list index out of range')

        if index >= self.page_size * self.max_pages:
            raise IndexError('list index out of range')
        normalized_index = index % self.page_size
        target_page = math.ceil((index+1.0)/self.page_size)-1
        target_page = int(target_page)

        if not self.lists[target_page]:
            self._load_page(target_page)

        return self.lists[target_page][normalized_index]

    def __len__(self):
        return self.total_items

    def _get_slice(self, s):
        # get range
        i = s.start if s.start is not None else 0
        j = s.stop if s.stop is not None else self.total_items

        # we do not support steps outside of 1 yet
        if s.step is not None and s.step != 1:
            raise NotImplementedError('TODO')

        # if i or j are negative, normalize them
        if i < 0:
            i = self.total_items + i

        if j < 0:
            j = self.total_items + j

        # if i or j are still negative, that's an IndexError
        if i < 0 or j < 0:
            raise IndexError('list index out of range')

        # if we're going nowhere or backward, return nothing
        if j <= i:
            return []

        result = []

        for c in range(i, j):
            result.append(self[c])

        return result

    def __setitem__(self, index, value):
        raise AttributeError('Assigning to indicies in paginated lists is not supported')

    def __delitem__(self, index, value):
        raise AttributeError('Assigning to indicies in paginated lists is not supported')

    def __next__(self):
        if self.cur < len(self):
            self.cur += 1
            return self[self.cur-1]
        else:
            raise StopIteration()

    @staticmethod
    def make_list(json_arr, client, cls, parent_id=None):
        """
        Returns a list of Populated objects of the given class type.

        :param json_arr: The array of JSON data to make into a list
        :param client: The LinodeClient to pass to new objects
        :param parent_id: The parent id for derived objects

        :returns: A list of models from the JSON
        """
        result = []

        for obj in json_arr:
            id_val = None

            if 'id' in obj:
                id_val = obj['id']
            elif hasattr(cls, 'id_attribute') and getattr(cls, 'id_attribute') in obj:
                id_val = obj[getattr(cls, 'id_attribute')]
            else:
                continue
            o = cls.make_instance(id_val, client, parent_id=parent_id, json=obj)
            result.append(o)

        return result

    @staticmethod
    def make_paginated_list(json, client, cls, parent_id=None, page_url=None,
            filters=None):
        """
        Returns a PaginatedList populated with the first page of data provided,
        and the ability to load more.

        :param json: The JSON list to use as the first page
        :param client: A LinodeClient to use to load additional pages
        :param parent_id: The parent ID for derived objects
        :param page_url: The URL to use when loading more pages
        :param cls: The class to instantiate for objects
        :param filters: The filters used when making the call that generated
                        this list.  If not provided, this will fail when
                        loading additional pages.

        :returns: An instance of PaginatedList that will represent the entire
                  collection whose first page is json
        """
        l = PaginatedList.make_list(json["data"], client, cls, parent_id=parent_id)
        p = PaginatedList(client, page_url, page=l, max_pages=json['pages'],
                total_items=json['results'], parent_id=parent_id, filters=filters)
        return p
