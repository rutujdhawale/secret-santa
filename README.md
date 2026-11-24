# 🎅 SantaSwarm — Secret Santa that shops at Cerebras speed

Add SantaSwarm to your WhatsApp or Telegram group. Everyone drops their interests, the agent draws names privately, and it returns **real, verified gift links within budget for every person in seconds**. It's built on **OpenClaw** + **Kimi K3.1 Pro on Cerebras**.

```
santa-swarm/
├── skills/secret-santa/SKILL.md        # the OpenClaw skill (agent instructions)
├── skills/secret-santa/scripts/santa.py # group state, name draw, link checker (stdlib)
└── demo/race.py                         # Cerebras vs GPU side-by-side race for the video
```

## 1. Setup (≈10 min)

```bash
# OpenClaw + Cerebras provider
openclaw plugins install @openclaw/cerebras-provider
echo 'CEREBRAS_API_KEY=csk-...' >> ~/.openclaw/.env
openclaw gateway restart
openclaw models list --provider cerebras   # confirm the Kimi trial model shows up
```

Then set Kimi as the default model in `~/.openclaw/openclaw.json`:

```json5
{
  agents: { defaults: { model: { primary: "cerebras/moonshotai-kimi-k3.1-pro-trial" } } },
  models: {
    mode: "merge",
    providers: {
      cerebras: {
        baseUrl: "https://api.cerebras.ai/v1",
        apiKey: "${CEREBRAS_API_KEY}",
        api: "openai-completions",
        // Only needed if discovery doesn't list it:
        models: [{ id: "moonshotai-kimi-k3.1-pro-trial", name: "Kimi K3.1 Pro (trial)" }],
      },
    },
  },
}
```

Install the skill and connect a chat app:

```bash
cp -r skills/secret-santa ~/.openclaw/workspace/skills/
openclaw channels login        # pick Telegram (fastest to set up) or WhatsApp
openclaw gateway restart
```

Make sure OpenClaw's web search tool is enabled. The skill depends on it to find real products. In groups, mention the bot (`@SantaSwarm ...`) unless you've turned off mention-gating.

## 2. Try it

```
@SantaSwarm start secret santa, $40 budget
I'm in — I like hiking and coffee          (each friend)
@SantaSwarm draw names
@SantaSwarm find gifts for everyone
```

Smoke-test the helper without the agent:

```bash
S="python3 skills/secret-santa/scripts/santa.py"
$S setup --group test --budget 40
$S join --group test --name Priya --likes "hiking, coffee"
$S join --group test --name Arjun --likes "lego"
$S draw --group test
$S check-links https://www.amazon.com/dp/B000IGOXLS
```

## 3. Speed Bounty run (Santa's Speedy Shopper)

Send `find 5 christmas gifts` to the bot. The skill's **Speed run** section makes it search all 5 categories in parallel and verify links in one call. Before you record:

- Use the **official speed patch** for this run only, and post it to Discord `#share-your-demo` with "Speed Bounty entry: N TPS".
- Keep reasoning **off** (the Cerebras default).
- Run it 3–5 times and submit your best. Earlier runs warm the prompt cache.

## 4. Demo video (≤60 s) shot list

| Time | Shot |
|---|---|
| 0–3 s | Hook text: **"Our whole Secret Santa, shopped in 4 seconds."** Phone showing the group chat |
| 3–15 s | 4 friends send their likes; "@SantaSwarm draw names" → "check your DMs 🎅" |
| 15–30 s | "find gifts for everyone" → 12 real gift links appear almost instantly. Add a stopwatch overlay |
| 30–45 s | `python3 demo/race.py` split-screen: Cerebras done while the GPU lane is still typing |
| 45–55 s | Tap one link → real product page opens, in budget |
| 55–60 s | "SantaSwarm · Kimi K3.1 Pro on Cerebras · OpenClaw" + repo link |

Add burned-in captions, since most viewers watch muted. Record with **standard OpenClaw**, not the patch. Hide your API keys, notifications and personal chats.

Race setup:

```bash
export CEREBRAS_API_KEY=csk-...
export GPU_BASE_URL=https://<gpu-provider>/v1 GPU_API_KEY=... GPU_MODEL=<their Kimi model>
export GPU_LABEL="Kimi on GPU"
python3 demo/race.py
```

## 5. Post templates

**X** (required, by Sun Nov 22, 10:00 AM PT / 11:30 PM IST):

> Our friend group's entire Secret Santa — names drawn, 12 real gifts found, all under budget — in ~4 seconds 🎅⚡
>
> SantaSwarm lives in your group chat. Built on OpenClaw + Kimi K3.1 Pro on @Cerebras.
>
> Project: SantaSwarm · Team: @you
> Repo: github.com/rutujdhawale/secret-santa
>
> #KimiOnCerebras @Cerebras @Kimi_Moonshot

**Reddit** (r/cerebras, flair "Kimi K3.1 Pro Hackathon"): use the same video, title it something like *"I let an AI run our Secret Santa in a WhatsApp group — it found 12 real gifts before I finished my chai"*, and add the setup steps in the body.

## Stretch ideas, if time allows

- **Budget mixer:** "split $40 as $25 gift + $15 stocking stuffer".
- **Anti-repeat:** remember last year's pairs and avoid them.
- **Wishlist from photos:** a friend sends a picture of their desk or shelf, and the agent infers their interests.
- **Live leaderboard:** a web page that shows each person's gifts as the agent finds them.
