import sys
import traceback
import re
import mwparserfromhell as mw
import api
import util
from typing import *
import urllib.request

"this isn't quite right, because 2h, but the format isn't smart enough for that"
slotIDs: Dict[str, int] = {
	"weapon": 3,
	"2h": 3,
	"body": 4,
	"head": 0,
	"ammo": 13,
	"legs": 7,
	"feet": 10,
	"hands": 9,
	"cape": 1,
	"neck": 2,
	"ring": 12,
	"shield": 5
}

WEIGHT_REDUCTION_EXTRACTOR = re.compile(
	r"(?i)'''(?:In )?inventory:?''':? ([0-9.-]+) kg<br ?\/?> *'''Equipped:?''':? ([0-9.-]+)")


def getLimits():
	req = urllib.request.Request(
		'https://oldschool.runescape.wiki/w/Module:GELimits/data?action=raw', headers=api.user_agent)
	with urllib.request.urlopen(req) as response:
		data = response.read()
	limits = {}
	for line in data.splitlines():
		match = re.search(r"\[\"(.*)\"\] = (\d+),?", str(line))
		if match:
			name = match.group(1).replace('\\', '')
			limit = match.group(2)
			limits[name] = int(limit)
	return limits


def run():
	limits = getLimits()
	stats = {}

	item_pages = api.query_category("Items")
	for name, page in item_pages.items():
		if name.startswith("Category:"):
			continue

		try:
			code = mw.parse(page, skip_style_tags=True)

			equips = {}
			for (vid, version) in util.each_version("Infobox Bonuses", code):
				doc = {}
				equips[vid] = doc

				slotID = str(version["slot"]).strip().lower()
				doc["slot"] = slotIDs[slotID]
				if slotID == "2h":
					doc["is_2h"] = True

				for key in [
					"astab", "aslash", "acrush", "amagic", "arange", "dstab", "dslash", "dcrush", "dmagic", "drange", "str",
					"rstr", "mdmg", "prayer", ("speed", "aspeed")
				]:
					try:
						util.copy(key, doc, version, lambda x: int(x))
					except ValueError:
						print("Item {} has an non integer {}".format(name, key))

			for (vid, version) in util.each_version("Infobox Item", code):
				if "removal" in version and str(version["removal"]).strip():
					continue

				doc = util.get_doc_for_id_string(name + str(vid), version, stats)
				if doc == None:
					continue

				util.copy("name", doc, version)
				if not "name" in doc:
					doc["name"] = name

				util.copy("quest", doc, version, lambda x: x.lower() != "no")

				equipable = "equipable" in version and "yes" in str(version["equipable"]).strip().lower()

				if "weight" in version:
					strval = str(version["weight"]).strip()
					if strval.endswith("kg"):
						strval = strval[:-2].strip()
					if strval != "":
						red = WEIGHT_REDUCTION_EXTRACTOR.match(strval)
						if red:
							strval = red.group(2)
						floatval = float(strval)
						if floatval != 0:
							doc["weight"] = floatval

				equipVid = vid if vid in equips else -1 if -1 in equips else None
				if equipVid != None:
					if equipable or not "broken" in version["name"].lower():
						if not equipable:
							print("Item {} has Infobox Bonuses but not equipable".format(name))
						doc["equipable"] = True
						doc["equipment"] = equips[equipVid]
				elif equipable:
					print("Item {} has equipable but not Infobox Bonuses".format(name))
					doc["equipable"] = True
					doc["equipment"] = {}

				itemName = name
				if "gemwname" in version:
					itemName = str(version["gemwname"]).strip()
				elif "name" in version:
					itemName = str(version["name"]).strip()
				if itemName in limits:
					doc['ge_limit'] = limits[itemName]

		except (KeyboardInterrupt, SystemExit):
			raise
		except:
			print("Item {} failed:".format(name))
			traceback.print_exc()

	util.write_json("stats.json", "stats.ids.min.json", stats)
