# Places data (GeoNames) and the re-import runbook

Status: re-imported on production 2026-11-28 with spelling-tolerant Hindi search (commit `b6f8cc8`).

## What is stored
`places` (one row per GeoNames populated place in India, about 558,000) and `place_names` (normalised search names,
about 585,000). Data: GeoNames, CC BY 4.0, credited in the API response and in the app.

## How Hindi search works
- The importer keeps **every** Hindi name GeoNames has for a place (up to 6, preferred first) and puts them right after
  the primary names, before the alternates, so the 16-name cap per place can never cut them off.
- `places/normalize.py` treats equivalent Devanagari spellings as one, for stored names and queries alike:
  chandrabindu and anusvara (गुड़गाँव = गुड़गांव), nasal + virama and anusvara (इन्दौर = इंदौर, मुम्बई = मुंबई), and the
  nukta (गुड़गांव = गुडगांव).
- `places/aliases.py` adds common spellings GeoNames lacks for 12 major cities (बेंगलुरु, गुड़गांव, बॉम्बे, ...). The
  first Hindi name in an entry is the one shown. An entry applies only if the English name matches, so a wrong id
  cannot rename another place.
- Search also matches `places.name_hi` directly (indexed), which covered places imported before this fix.
- A test sweeps 25 major cities by their usual Hindi spelling (25 of 25 on the real data, before and after deploy).

## Re-importing on Railway (when normalisation or aliases change)
The importer upserts in place, so saved home cities survive. Anything that changes `normalize()` needs a re-import,
because stored names were normalised with the old rules.
1. Deploy the code first (the importer in the container is the deployed one).
2. Generate a temporary key in `~/.ssh` (the Railway CLI only finds keys there) and register it:
   `ssh-keygen -t ed25519 -N "" -f ~/.ssh/astrodaily_temp_reimport` then
   `railway ssh keys add --key ~/.ssh/astrodaily_temp_reimport --name astrodaily-temp-reimport`.
3. Write the SSH config to a scratch file, not `~/.ssh/config`:
   `railway ssh config --service AstroDailyAGPL --path /some/scratch/ssh_config --alias astro-railway`. Connect with
   `ssh -F <that file> -i <key> -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=<scratch> astro-railway`
   (first contact trusts the host key once; later calls use `StrictHostKeyChecking=yes`).
4. Record counts, then run in the background so a dropped connection cannot interrupt it:
   `nohup python -m astrodaily.tools.import_geonames --country IN > /tmp/reimport.log 2>&1 &` (about 2 minutes; the
   container has no `pgrep`, check `/proc/<pid>`).
5. Verify against the live API (the city sweep), then **remove the key**: `railway ssh keys remove <fingerprint>`,
   delete both key files, delete the scratch config and known-hosts files, and check `railway ssh keys list` is empty.
