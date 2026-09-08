# networks/

Chain marks for the deposit and withdraw network pickers — one per network
document in the app's `hyperliquidnetworks` collection (89 as of this commit).

## Naming

Filenames are a slug of the network's **canonical name**, which is the
`networkName` the API serves:

| Network | File |
|---|---|
| `Arbitrum One` | `arbitrum-one.webp` |
| `B² Network` | `b2-network.webp` |
| `KAVA EVM` | `kava-evm.webp` |
| `opBNB` | `opbnb.webp` |

The rule: fold `²³¹` to digits, strip accents, replace every run of
non-alphanumerics with `-`, lowercase. `_networks.json` records the
network-name → filename mapping that was actually built, and the frontend's
`src/config/networkIcons.js` carries the same slug function plus an alias table
for the exchange chain CODES (`BSC`, `MATIC`, `ARBITRUM`) that do not slug to a
canonical name on their own.

## Format

144x144 lossless WebP with alpha, same as the rest of the repo. Sources ranged
from a 21 px favicon to a 512 px master, so each was cropped to its visible
pixels and rescaled to fill the canvas — without that, the small favicons
rendered at a quarter the size of everything else in a 20 px list.

Regenerate from `docs/Assets/Networks Favicons/` in the main workspace rather
than editing these by hand.
