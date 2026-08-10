# aws-lambda-telemetry-eventbridge-enrichment

[![Brought to you by Telemetry Team](https://img.shields.io/badge/MDTP-Telemetry-40D9C0?style=flat&labelColor=000000&logo=gov.uk)](https://confluence.tools.tax.service.gov.uk/display/TEL/Telemetry)

Multipurpose EventBridge enrichment Lambda. The purpose of this function is to take events from EventBridge sources,
enrich the contents of the event and then allow the pipe to pass the event onto the target

## Table of Contents
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [License](#license)

<!-- END doctoc -->

## Prerequisites

* [mise](https://mise.jdx.dev/) to manage tool versions and integrates with `uv`.
* [uv](https://docs.astral.sh/uv/) to manage Python virtual environments and dependencies.

## Quick start

Install dependencies using uv:

```shell
mise run setup
# Run tests:
mise run test
# Package the lambda locally:
mise run package
```

## License

This code is open source software licensed under the [Apache 2.0 License]("http://www.apache.org/licenses/LICENSE-2.0.html").
