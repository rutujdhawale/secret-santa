---
name: secret-santa
description: Run a Secret Santa for a group chat and find real, buyable gifts fast. Use when someone mentions secret santa, a wishlist, a gift budget, drawing names, or asks for Christmas/holiday gift ideas for a person.
---

# Secret Santa

You run a Secret Santa for the chat you are in, and you find **real products from real retail sites** for each person. Speed is the whole point, so keep replies short and do work in parallel.

The helper script keeps the group's state, so you never have to remember it yourself:

```
python3 {baseDir}/scripts/santa.py <command> --group <GROUP_ID> ...
```

Use the chat/channel id as `GROUP_ID`. Every command prints JSON. Trust the JSON, not your memory.

## Commands people will type

| They say | You run |
|---|---|
| "start secret santa, $40 budget" | `setup --budget 40 --currency USD` (default currency USD; use INR if they write ₹) |
| "I'm in, I like hiking and coffee" | `join --name "<sender name>" --likes "hiking, coffee"` |
| "add to my list: lego" | `wish --name "<sender name>" --likes "lego"` |
| "who's in?" / "status" | `status` |
| "draw names" | `draw`, then see **Drawing names** |
| "find gifts for Priya" / "gift ideas" | see **Finding gifts** |
| "find 5 christmas gifts" (no group) | see **Speed run** |

## Drawing names

1. Run `draw`. It returns `pairs` of `{giver, receiver}`.
2. Do **not** post the pairs in the group — that ruins the surprise.
3. If you can message people privately on this channel, DM each giver only their receiver plus that person's likes. Otherwise send the full list only to the person who asked for the draw, and tell the group "Names drawn — check your DMs 🎅".

## Finding gifts

For each person you are asked about:

1. Read their likes and the budget from `status`.
2. Search the web for **3 candidate products per person, all at once** (fire your searches in parallel, one query per interest, e.g. `"pour over coffee kit under $40"`). Prefer big real retailers: Amazon, Target, Etsy, Walmart, Best Buy, REI, Uncommon Goods, Flipkart, Myntra, Nykaa.
3. Only keep links that go to a **single product page** (not search results, categories or blog listicles).
4. Verify every link before you post it:
   `python3 {baseDir}/scripts/santa.py check-links <url1> <url2> ...`
   Drop anything with `"status": "dead"`. `"unverified"` means the store blocked the check — keep it only if the page title came from a real search result.
5. Never invent a product, price or URL. If you can't confirm a price, write "price varies".
6. Save picks: `save-gifts --name "<person>" --json '<list>'` where the list is `[{"title":..., "price":..., "store":..., "url":...}]`.

Reply format, one block per person, nothing else:

```
🎁 Priya (hiking, coffee · $40)
1. Hario V60 Pour-Over Kit — $29 · Amazon
   <url>
2. ...
```

## Speed run

When asked for "5 Christmas gifts" with no group context, skip the group state entirely:

1. Pick 5 different gift categories yourself (a gadget, a cozy item, a book, a game, a kitchen item).
2. Search for all 5 in parallel, take one real product page per category.
3. Run `check-links` once on all 5 URLs together.
4. Post the 5 in the reply format above with a 🎄 header. No preamble, no closing paragraph.

## Style

- Short, warm, a little festive. One emoji per line at most.
- No long explanations. The list is the answer.
- Don't think out loud; act.
