# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from hashlib import md5
from    json import loads
from      os import popen, getenv

class Env:

    def GetAccount():

        result = loads(popen('aws sts get-caller-identity --output json').read() or '{}')

        return result.get('Account', 'error').strip()

    def GetRegion():

        result = popen('aws configure get region --output text').read() or 'error'

        return result.strip()

    def GetPrefix():

        return f'mcp'

    def GetSuffix():

        account = Env.GetAccount()
        suffix  = f'{account}'        

        return suffix.lower()

    def GetUnique():

        suffix  = Env.GetSuffix()
        hashed  = md5(suffix.encode()).hexdigest()

        return hashed