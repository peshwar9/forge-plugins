# Reporting a security problem

If you find a security problem in anything in this repository, or in the endpoint the
`forge-pii-scan` plugin connects to, please tell us.

**Email `contact@gradtensor.com` with "security" in the subject.** It reaches the person who
maintains this, which at present is one person, so it will not sit in a queue.

Please do not open a public issue for something exploitable. Tell us first and give us a
chance to fix it.

## What to expect

We will acknowledge your report within three working days, tell you whether we can reproduce
it within ten, and keep you informed while we work on it. We will tell you when it is fixed,
and we are glad to credit you unless you would rather we did not.

We are a small team and we will say so honestly if something will take time. We would rather
give you a slow answer than no answer.

## What is in scope

- `https://www.forgeprivate.com/api/mcp/public`, the endpoint the plugin uses
- Anything in this repository: the plugin manifest, the skill, the MCP server reference

**The thing we care about most** is anything suggesting that text sent to the scan endpoint
is stored, logged, cached, or recoverable after the reply is sent. We state publicly that it
is not, in the tool's own output, in the README, and in our
[privacy policy](https://www.forgeprivate.com/privacy). If any of that is wrong, it is the
most serious report you could send us, and we want it.

Also worth reporting: anything that makes the endpoint return another caller's data, anything
that lets a report include an identifier's value rather than only its kind and location, and
anything that makes the service a useful amplifier against somebody else.

## What is not a vulnerability

**A name written in an ordinary sentence is not detected.** This is by design and documented
everywhere the tool is described. Names and addresses are found through the shape of a
document, such as a table column headed Name, a signature block or a postcode, and never by
recognising a name in prose. A missed name in a sentence is the tool working as described.

Missed or over-eager matches of other kinds are worth reporting as bugs rather than
vulnerabilities, through a GitHub issue.

The rate limit is per server instance and does not hold across them. We know, we say so in
the code, and it exists to stop an accident rather than an attacker.

## The product behind it

The scan endpoint belongs to [Forge](https://www.forgeprivate.com), a private workspace for
confidential work. A report about Forge itself rather than this plugin goes to the same
address.
