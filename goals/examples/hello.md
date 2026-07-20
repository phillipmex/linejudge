---
name: hello
tags:
  - example
verifiers:
  - command: python -c "assert open('hello.txt').read().strip() == 'hello from the agent'"
timeout_secs: 300
---
Create a file named `hello.txt` in your working directory containing exactly:

    hello from the agent

Then write your REPORT.md per the output contract.
