from .dbase import DerivedBase
from .base import Property

class Disk(DerivedBase):
    api_endpoint = '/linodes/{linode_id}/disks/{id}'
    derived_url_path = 'disks'
    parent_id_name='linode_id'

    properties = {
        'id': Property(identifier=True),
        'created': Property(is_datetime=True),
        'label': Property(mutable=True),
        'size': Property(),
        'status': Property(),
        'type': Property(),
        'updated': Property(is_datetime=True),
        'linode_id': Property(identifier=True),
    }


    def duplicate(self):
        result = self._client.post(Disk.api_endpoint, model=self, data={})

        if not 'disk' in result:
            return result

        d = Disk(self._client, result['disk']['id'], self.linode_id)
        d._populate(result['disk'])
        return d


    def reset_root_password(self, root_password=None):
        rpass = root_password
        if not rpass:
            from .linode import Linode
            rpass = Linode.generate_root_password()

        params = {
            'password': rpass,
        }

        result = self._client.post(Disk.api_endpoint, model=self, data=params)

        if not 'disk' in result:
            if not root_password:
                return result, rpass
            return result

        self._populate(result['disk'])
        if not root_password:
            return True, rpass
        return True
