# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
__copyright__ = ('Copyright Amazon.com, Inc. or its affiliates. '
                 'All Rights Reserved.')
__version__ = '2.5.1-beta.2'
__license__ = 'MIT-0'
__author__ = 'Akihiro Nakajima'
__url__ = 'https://github.com/aws-samples/siem-on-amazon-opensearch-service'

import re
from functools import cached_property

from aws_lambda_powertools import Logger

from siem import FileFormatBase

logger = Logger(child=True)


class FileFormatMultiline(FileFormatBase):
    def __init__(self, rawdata=None, logconfig=None, logtype=None):
        super().__init__(rawdata, logconfig, logtype)
        self._multiline_firstline = None

    @cached_property
    def _re_log_pattern_prog(self):
        try:
            return self.logconfig['log_pattern']
        except AttributeError:
            msg = 'No log_pattern(regex). You need to define it in user.ini'
            logger.exception(msg)
            raise AttributeError(msg) from None

    @property
    def multiline_firstline(self):
        return self._multiline_firstline

    @multiline_firstline.setter
    def multiline_firstline(self, multiline_firstline):
        self._multiline_firstline = multiline_firstline

    @cached_property
    def _re_multiline_firstline(self):
        if self.logconfig:
            return self.logconfig['multiline_firstline']
        elif self.multiline_firstline:
            return re.compile(self.multiline_firstline)

    @property
    def log_count(self):
        count = 0
        for line in self.rawdata:
            if self._match_multiline_firstline(line):
                count += 1
        return count

    def _match_multiline_firstline(self, line):
        if self._re_multiline_firstline.match(line):
            return True
        else:
            return False

    def extract_log(self, start, end, logmeta={}):
        count = 0
        multilog = []
        is_in_scope = False
        for line in self.rawdata:
            if self._match_multiline_firstline(line):
                count += 1
                if start <= count <= end:
                    if len(multilog) > 0:
                        # yield previous log
                        lograw = "".join(multilog).rstrip()
                        logdict = self.convert_lograw_to_dict(lograw)
                        yield(lograw, logdict, logmeta)
                    multilog = []
                    is_in_scope = True
                    multilog.append(line)
                else:
                    continue
            elif is_in_scope:
                multilog.append(line)
        if is_in_scope:
            # yield last log
            lograw = "".join(multilog).rstrip()
            logdict = self.convert_lograw_to_dict(lograw)
            yield(lograw, logdict, logmeta)

    def convert_lograw_to_dict(self, lograw, logconfig=None):
        m = self._re_log_pattern_prog.match(lograw)
        if m:
            logdata_dict = m.groupdict()
        else:
            msg_dict = {
                'Exception': f'Invalid regex pattern of {self.logtype}',
                'rawdata': lograw, 'regex_pattern': self._re_log_pattern_prog}
            logger.error(msg_dict)
            raise Exception(repr(msg_dict))
        return logdata_dict