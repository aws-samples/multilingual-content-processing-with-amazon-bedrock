#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import aws_cdk as cdk

from pathlib      import Path

from infra.standard_utils import Env
from infra.baseline_stack import BaselineStack # common s3bucket resource
from infra.template_stack import TemplateStack # worker template resource
from infra.pipeline_stack import PipelineStack


prefix = Env.GetPrefix()
suffix = Env.GetSuffix()

if  __name__ == '__main__':

    app     = cdk.App()

    baseline_stack = BaselineStack(
        scope  = app,
        id     = f'{prefix}-Baseline',
        prefix = prefix,
        suffix = suffix
    )

    template_stack = TemplateStack(
        scope  = app,
        id     = f'{prefix}-Template',
        prefix = prefix,
        suffix = suffix,
        source = Path('source/augment-ui').absolute()
    )

    pipeline_stack = PipelineStack(
        scope  = app,
        id     = f'{prefix}-Pipeline',
        prefix = prefix,
        suffix = suffix,
        source = Path('source/lambdas').absolute(),
        liquid = template_stack.get_resources()['liquid_uri']
        # liquid = None
    )

    template_stack.add_dependency(baseline_stack)
    pipeline_stack.add_dependency(baseline_stack)
    pipeline_stack.add_dependency(template_stack)

    app.synth()
