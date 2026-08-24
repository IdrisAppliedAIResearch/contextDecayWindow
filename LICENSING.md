# Licensing

`contextDecayWindow` is **dual licensed**. You may use it under either:

1. the **GNU Affero General Public License, version 3 or later** (AGPL-3.0-or-later),
   the full text of which is in [`LICENSE`](LICENSE); or
2. a **commercial licence** from Idris Applied AI Research, which removes the
   AGPL's source-disclosure obligations.

You choose. If you do nothing, the AGPL applies.

Copyright © 2026 Idris Applied AI Research. All rights reserved.

---

## Which one do you need?

The AGPL is a strong copyleft licence. Its practical effect here is one clause
most permissive licences do not have — **section 13, remote network
interaction**:

> if you modify the Program, your modified version must prominently offer all
> users interacting with it remotely through a computer network (if your version
> supports such interaction) an opportunity to receive the Corresponding Source
> of your version by providing access to the Corresponding Source from a network
> server at no charge

For a memory layer this is the clause that matters, because the usual way to
deploy one is behind a network service where no binary is ever distributed.
Under a permissive licence that would carry no obligation. Under the AGPL it
does.

**The AGPL is enough if:**

- you are evaluating, researching, teaching, or reproducing the published results;
- your own project is released under the AGPL-3.0-or-later as well;
- you run it internally and never expose it to third parties over a network;
- you are building something you intend to open-source on compatible terms.

**You need a commercial licence if:**

- you offer a hosted or SaaS product that users reach over a network, and you do
  not want to release your service's source under the AGPL;
- you embed it in a proprietary product you distribute to customers;
- you link it into a closed-source codebase;
- your organisation's policy prohibits AGPL code regardless of how it is used.

If you are unsure which side of the line you fall on, ask before you build.
The answer is usually quick and it is cheaper than finding out later.

## Getting a commercial licence

Contact **idrisappliedairesearch@gmail.com** with a short description of what
you are building and how it will be deployed.

A commercial licence grants you the same software under terms that waive the
copyleft and network-disclosure requirements. It does not change the software
itself, and it does not buy an exception to the warranty disclaimer: the code
is provided as-is under either licence.

## What is covered

The dual licence covers the entire repository — source code, tests, the
documentation, and the paper and its supporting material — with two exceptions.

**Third-party datasets are not ours to license.** Material derived from or
reproduced out of LoCoMo, LongMemEval, and any other external corpus remains
under its own upstream terms. This includes the conversation text carried in the
comparison artifacts under `experiments/comparisons/` and the material under
`experiments/external/`. Nothing here grants you rights to that data; obtain it
from its own source under its own licence.

**Third-party dependencies keep their own licences.** The runtime and
development dependencies are permissively licensed (MIT, BSD-3-Clause,
Apache-2.0, and PSF), which is what makes the AGPL choice available in the first
place. Model weights — the llama.cpp GGUF and embedding models named in the
runtime notes — are licensed by their publishers and are not distributed here.

## Contributions

Dual licensing only works if a single party can relicense the whole work. By
opening a pull request you agree that your contribution is licensed to Idris
Applied AI Research under the AGPL-3.0-or-later **and** that Idris Applied AI
Research may also distribute it under the commercial licence described above.
You keep the copyright in what you wrote.

If you cannot make that grant — because an employer owns your output, or for any
other reason — say so in the pull request before it is reviewed.

## The research record

Licensing changes what you may do with this repository. It changes nothing about
what the repository claims. The studies, their pre-registrations, their
amendments and their failures stay exactly as recorded, under either licence.
