# aws-lambda-telemetry-eventbridge-enrichment

[![Brought to you by Telemetry Team](https://img.shields.io/badge/MDTP-Telemetry-40D9C0?style=flat&labelColor=000000&logo=gov.uk)](https://confluence.tools.tax.service.gov.uk/display/TEL/Telemetry)

Multipurpose EventBridge enrichment Lambda. The purpose of this function is to take events from EventBridge sources, 
enrich the contents of the event and then allow the pipe to pass the event onto the target

Please check the [telemetry-terraform](https://github.com/hmrc/telemetry-terraform) repository for details on how this Lambda is deployed.

## Requirements

* [Python 3.9+](https://www.python.org/downloads/release)
* [Poetry](https://python-poetry.org/)


### License

This code is open source software licensed under the [Apache 2.0 License]("http://www.apache.org/licenses/LICENSE-2.0.html").
