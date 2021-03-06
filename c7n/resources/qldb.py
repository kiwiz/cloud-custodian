# Copyright 2020 Cloud Custodian Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from c7n.actions import BaseAction as Action
from c7n.query import DescribeSource, QueryResourceManager, TypeInfo
from c7n.manager import resources
from c7n.tags import universal_augment
from c7n.utils import local_session, type_schema


@resources.register('qldb')
class QLDB(QueryResourceManager):

    class resource_type(TypeInfo):
        service = 'qldb'
        enum_spec = ('list_ledgers', 'Ledgers', None)
        detail_spec = ('describe_ledger', 'Name', 'Name', None)
        arn_type = 'ledger'
        id = name = 'Name'
        date = 'CreationDateTime'
        universal_taggable = object()
        config_type = 'AWS::QLDB::Ledger'
        not_found_err = 'ResourceNotFoundException'

    def get_source(self, source_type):
        source = super().get_source(source_type)
        if source_type == 'describe':
            source = DescribeQLDB(self)
        return source


class DescribeQLDB(DescribeSource):

    def augment(self, resources):
        return universal_augment(self.manager, super().augment(resources))


@QLDB.action_registry.register('delete')
class Delete(Action):

    schema = type_schema('delete', force={'type': 'boolean'})
    permissions = ('qldb:DeleteLedger', 'qldb:UpdateLedger')

    def process(self, resources):
        client = local_session(self.manager.session_factory).client('qldb')
        protected = 0
        for r in resources:
            if r.get('DeletionProtection') and self.data.get('force'):
                try:
                    client.update_ledger(
                        Name=r['Name'],
                        DeletionProtection=False)
                except self.manager.resource_type.not_found_err:
                    continue
            elif r.get('DeletionProtection'):
                protected += 1
                continue
            try:
                client.delete_ledger(Name=r['Name'])
            except self.manager.resource_type.not_found_err:
                continue
        if protected:
            self.log.warning((
                'qldb delete found %d delete-protected resources, '
                'configure force: true to delete'), protected)
