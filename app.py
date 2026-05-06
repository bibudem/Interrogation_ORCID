"""
Application Flask — Explorateur ORCID v2
Opérations : Lecture complète de profil + Recherche + Export CSV/JSON
Environnement : sélectionnable via l'interface (sandbox / production)
"""

import csv
import io
import json
import re
import time
import requests
from flask import Flask, render_template, request, jsonify, session, Response

app = Flask(__name__)
app.secret_key = "orcid-explorer-dev-key-change-in-prod"

# ── Configuration ──────────────────────────────────────────────────────────────

ENVIRONMENTS = {
    "sandbox": {
        "label": "Sandbox",
        "base_url": "https://pub.sandbox.orcid.org/v3.0",
        "orcid_base": "https://sandbox.orcid.org",
        "color": "#f59e0b",
        "text_color": "#78350f",
    },
    "production": {
        "label": "Production",
        "base_url": "https://pub.orcid.org/v3.0",
        "orcid_base": "https://orcid.org",
        "color": "#1a6b4a",
        "text_color": "#fff",
    },
}

HEADERS = {"Accept": "application/json"}
DEMO_ORCID = "0000-0002-1825-0097"


def get_env() -> str:
    return session.get("env", "sandbox")


def get_client():
    base_url = ENVIRONMENTS[get_env()]["base_url"]
    return OrcidClient(base_url)


# ── Client ORCID ───────────────────────────────────────────────────────────────

class OrcidClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}/{path}"
        resp = self.session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_record(self, orcid_id: str) -> dict:
        return self._get(f"{orcid_id}/record")

    def get_person(self, orcid_id: str) -> dict:
        return self._get(f"{orcid_id}/person")

    def get_works(self, orcid_id: str) -> dict:
        return self._get(f"{orcid_id}/works")

    def get_employments(self, orcid_id: str) -> dict:
        return self._get(f"{orcid_id}/employments")

    def get_educations(self, orcid_id: str) -> dict:
        return self._get(f"{orcid_id}/educations")

    def get_fundings(self, orcid_id: str) -> dict:
        return self._get(f"{orcid_id}/fundings")

    def search(self, query: str, start: int = 0, rows: int = 25) -> dict:
        params = {"q": query, "start": start, "rows": rows}
        resp = self.session.get(f"{self.base_url}/search", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def search_all(self, query: str, batch_size: int = 100, delay: float = 0.3) -> list:
        orcid_ids = []
        first = self.search(query, start=0, rows=1)
        total = first.get("num-found", 0)
        if total == 0:
            return []
        start = 0
        while start < total:
            data = self.search(query, start=start, rows=batch_size)
            for r in (data.get("result") or []):
                oid = (r.get("orcid-identifier") or {}).get("path", "")
                if oid:
                    orcid_ids.append(oid)
            start += batch_size
            if start < total:
                time.sleep(delay)
        return orcid_ids


# ── Helpers d'extraction ───────────────────────────────────────────────────────

def extract_name(person: dict) -> str:
    name_obj = person.get("name") or {}
    given = (name_obj.get("given-names") or {}).get("value", "")
    family = (name_obj.get("family-name") or {}).get("value", "")
    credit = (name_obj.get("credit-name") or {}).get("value", "")
    return credit or f"{given} {family}".strip() or "Nom inconnu"


def extract_given_family(person: dict) -> tuple:
    name_obj = person.get("name") or {}
    given = (name_obj.get("given-names") or {}).get("value", "")
    family = (name_obj.get("family-name") or {}).get("value", "")
    return given, family


def extract_other_names(person: dict) -> list:
    """Autres noms / variantes de nom."""
    block = person.get("other-names") or {}
    items = block.get("other-name") or []
    return [i.get("content", "") for i in items if i.get("content")]


def extract_biography(person: dict) -> str:
    bio = person.get("biography") or {}
    return (bio.get("content") or "").strip()


def extract_keywords(person: dict) -> list:
    kw_block = person.get("keywords") or {}
    return [k.get("content", "") for k in (kw_block.get("keyword") or []) if k.get("content")]


def extract_country(person: dict) -> str:
    addresses = (person.get("addresses") or {}).get("address") or []
    if addresses:
        return (addresses[0].get("country") or {}).get("value", "")
    return ""


def extract_addresses(person: dict) -> list:
    """Tous les pays/adresses listés dans le profil."""
    addresses = (person.get("addresses") or {}).get("address") or []
    result = []
    for a in addresses:
        country = (a.get("country") or {}).get("value", "")
        visibility = a.get("visibility", "")
        if country:
            result.append({"country": country, "visibility": visibility})
    return result


def extract_emails(person: dict) -> list:
    emails_block = person.get("emails") or {}
    result = []
    for e in (emails_block.get("email") or []):
        addr = e.get("email", "")
        if addr:
            result.append({
                "email": addr,
                "primary": e.get("primary", False),
                "verified": e.get("verified", False),
                "visibility": e.get("visibility", ""),
            })
    # Trier : primaire en premier
    result.sort(key=lambda x: (not x["primary"]))
    return result


def extract_researcher_urls(person: dict) -> list:
    """Sites web / profils en ligne déclarés par le chercheur."""
    block = person.get("researcher-urls") or {}
    result = []
    for u in (block.get("researcher-url") or []):
        name = (u.get("url-name") or "")
        url = (u.get("url") or {}).get("value", "")
        if url:
            result.append({"name": name, "url": url})
    return result


def extract_external_identifiers(person: dict) -> list:
    """Identifiants externes : Scopus, ResearcherID, Loop, etc."""
    block = person.get("external-identifiers") or {}
    result = []
    for ei in (block.get("external-identifier") or []):
        id_type = ei.get("external-id-type", "")
        id_value = ei.get("external-id-value", "")
        id_url = (ei.get("external-id-url") or {}).get("value", "")
        if id_type and id_value:
            result.append({
                "type": id_type,
                "value": id_value,
                "url": id_url,
            })
    return result


def extract_works(works_data: dict) -> list:
    groups = works_data.get("group") or []
    result = []
    for group in groups:
        summaries = group.get("work-summary") or []
        if not summaries:
            continue
        s = summaries[0]
        title_obj = (s.get("title") or {}).get("title") or {}
        title = title_obj.get("value", "Sans titre")
        journal_obj = s.get("journal-title") or {}
        journal = journal_obj.get("value", "")
        pub_date = s.get("publication-date") or {}
        year = (pub_date.get("year") or {}).get("value", "")
        work_type = s.get("type", "")
        ext_ids = (s.get("external-ids") or {}).get("external-id") or []
        doi = ""
        doi_url = ""
        for eid in ext_ids:
            if eid.get("external-id-type") == "doi":
                doi = eid.get("external-id-value", "")
                doi_url = f"https://doi.org/{doi}" if doi else ""
                break
        url_obj = s.get("url") or {}
        url = url_obj.get("value", "") or doi_url
        result.append({
            "title": title,
            "journal": journal,
            "year": year,
            "type": work_type,
            "doi": doi,
            "url": url,
            "put_code": s.get("put-code"),
        })
    result.sort(key=lambda w: w["year"] or "0", reverse=True)
    return result


def extract_affiliations(employments_data: dict) -> list:
    groups = employments_data.get("affiliation-group") or []
    result = []
    for group in groups:
        for item in (group.get("summaries") or []):
            s = item.get("employment-summary") or {}
            org = (s.get("organization") or {}).get("name", "")
            dept = s.get("department-name") or ""
            role = s.get("role-title") or ""
            start_date = s.get("start-date") or {}
            end_date = s.get("end-date") or {}
            start_year = (start_date.get("year") or {}).get("value", "")
            end_year = (end_date.get("year") or {}).get("value", "") if end_date else "présent"
            # Identifiants d'organisation (ROR, Ringgold, GRID)
            org_ids = []
            disambig = ((s.get("organization") or {}).get("disambiguated-organization") or {})
            if disambig.get("disambiguated-organization-identifier"):
                org_ids.append({
                    "type": disambig.get("disambiguation-source", ""),
                    "value": disambig.get("disambiguated-organization-identifier", ""),
                })
            result.append({
                "organization": org,
                "department": dept,
                "role": role,
                "start_year": start_year,
                "end_year": end_year,
                "org_ids": org_ids,
            })
    return result


def extract_educations(educations_data: dict) -> list:
    groups = educations_data.get("affiliation-group") or []
    result = []
    for group in groups:
        for item in (group.get("summaries") or []):
            s = item.get("education-summary") or {}
            org = (s.get("organization") or {}).get("name", "")
            dept = s.get("department-name") or ""
            role = s.get("role-title") or ""  # Degree/diploma
            start_date = s.get("start-date") or {}
            end_date = s.get("end-date") or {}
            start_year = (start_date.get("year") or {}).get("value", "")
            end_year = (end_date.get("year") or {}).get("value", "") if end_date else ""
            if org:
                result.append({
                    "organization": org,
                    "department": dept,
                    "degree": role,
                    "start_year": start_year,
                    "end_year": end_year,
                })
    return result


def extract_fundings(fundings_data: dict) -> list:
    groups = fundings_data.get("group") or []
    result = []
    for group in groups:
        for s in (group.get("funding-summary") or []):
            title_obj = (s.get("title") or {}).get("title") or {}
            title = title_obj.get("value", "")
            ftype = s.get("type", "")
            org = (s.get("organization") or {}).get("name", "")
            start_date = s.get("start-date") or {}
            end_date = s.get("end-date") or {}
            start_year = (start_date.get("year") or {}).get("value", "")
            end_year = (end_date.get("year") or {}).get("value", "") if end_date else ""
            if title or org:
                result.append({
                    "title": title,
                    "type": ftype,
                    "organization": org,
                    "start_year": start_year,
                    "end_year": end_year,
                })
    return result


def build_full_profile(orcid_id: str, person: dict, works_data: dict,
                       employments_data: dict, educations_data: dict,
                       fundings_data: dict, env_info: dict) -> dict:
    """Construit le dictionnaire complet du profil pour affichage et export."""
    given, family = extract_given_family(person)
    works = extract_works(works_data)
    return {
        # Identité
        "orcid_id": orcid_id,
        "orcid_url": f"{env_info['orcid_base']}/{orcid_id}",
        "name": extract_name(person),
        "given_name": given,
        "family_name": family,
        "other_names": extract_other_names(person),
        # Contact & localisation
        "emails": extract_emails(person),
        "addresses": extract_addresses(person),
        # Identifiants externes
        "external_identifiers": extract_external_identifiers(person),
        # Présence en ligne
        "researcher_urls": extract_researcher_urls(person),
        # Description
        "biography": extract_biography(person),
        "keywords": extract_keywords(person),
        # Parcours
        "affiliations": extract_affiliations(employments_data),
        "educations": extract_educations(educations_data),
        "fundings": extract_fundings(fundings_data),
        # Publications
        "works": works,
        "works_count": len(works),
    }


def build_search_query(form: dict) -> str:
    parts = []
    if form.get("family_name"):
        parts.append(f'family-name:{form["family_name"]}')
    if form.get("given_name"):
        parts.append(f'given-names:{form["given_name"]}')
    if form.get("institution"):
        inst = form["institution"].replace('"', '\\"')
        parts.append(f'affiliation-org-name:"{inst}"')
    if form.get("keyword"):
        parts.append(f'keyword:{form["keyword"]}')
    if form.get("email"):
        parts.append(f'email:{form["email"].strip()}')
    if form.get("orcid_id"):
        parts.append(f'orcid:{form["orcid_id"]}')
    if form.get("free_query"):
        parts.append(form["free_query"])
    return " AND ".join(parts) if parts else "*:*"


def validate_orcid_id(orcid_id: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$", orcid_id.strip()))


# ── Context processor ──────────────────────────────────────────────────────────

@app.context_processor
def inject_env():
    env_key = get_env()
    return {
        "current_env": env_key,
        "env_info": ENVIRONMENTS[env_key],
        "environments": ENVIRONMENTS,
    }


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/set-env", methods=["POST"])
def set_env():
    env = request.form.get("env", "sandbox")
    if env in ENVIRONMENTS:
        session["env"] = env
    return Response("", status=302, headers={"Location": request.referrer or "/"})


@app.route("/")
def index():
    return render_template("index.html", demo_orcid=DEMO_ORCID)


@app.route("/profil", methods=["GET", "POST"])
def profil():
    data = None
    error = None
    orcid_id = None
    client = get_client()
    env_info = ENVIRONMENTS[get_env()]

    if request.method == "POST":
        raw = (request.form.get("orcid_id") or "").strip()
        raw = raw.replace("https://orcid.org/", "").replace("https://sandbox.orcid.org/", "")

        if not validate_orcid_id(raw):
            error = f"Format invalide : « {raw} ». Attendu : 0000-0000-0000-000X"
        else:
            orcid_id = raw
            try:
                person           = client.get_person(orcid_id)
                works_data       = client.get_works(orcid_id)
                employments_data = client.get_employments(orcid_id)
                educations_data  = client.get_educations(orcid_id)
                fundings_data    = client.get_fundings(orcid_id)

                data = build_full_profile(
                    orcid_id, person, works_data,
                    employments_data, educations_data, fundings_data,
                    env_info
                )
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    error = f"Aucun profil trouvé pour {orcid_id} dans l'environnement {env_info['label']}."
                elif e.response.status_code == 403:
                    error = "Ce profil n'est pas public."
                else:
                    error = f"Erreur API ORCID : {e.response.status_code}"
            except requests.exceptions.ConnectionError:
                error = f"Impossible de joindre l'API ORCID ({env_info['label']})."
            except Exception as e:
                error = f"Erreur inattendue : {str(e)}"

    return render_template("profil.html", data=data, error=error, orcid_id=orcid_id)


@app.route("/profil/<orcid_id>/export-json")
def export_json(orcid_id: str):
    """Télécharge le profil complet en JSON (données extraites + données brutes ORCID)."""
    if not validate_orcid_id(orcid_id):
        return jsonify({"error": "Format ORCID invalide"}), 400

    client = get_client()
    env_info = ENVIRONMENTS[get_env()]

    try:
        person           = client.get_person(orcid_id)
        works_data       = client.get_works(orcid_id)
        employments_data = client.get_employments(orcid_id)
        educations_data  = client.get_educations(orcid_id)
        fundings_data    = client.get_fundings(orcid_id)
        record_raw       = client.get_record(orcid_id)

        profile = build_full_profile(
            orcid_id, person, works_data,
            employments_data, educations_data, fundings_data,
            env_info
        )

        export = {
            "export_meta": {
                "source": "ORCID Explorer",
                "environment": env_info["label"],
                "orcid_api_version": "3.0",
                "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            "profile": profile,
            "raw_orcid_record": record_raw,
        }

        json_str = json.dumps(export, ensure_ascii=False, indent=2)
        filename = f"orcid_{orcid_id}.json"
        return Response(
            json_str,
            content_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": str(e)}), e.response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/recherche", methods=["GET", "POST"])
def recherche():
    results = None
    error = None
    total = 0
    query_str = ""
    form_data = {}
    client = get_client()

    if request.method == "POST":
        form_data = {
            "family_name": request.form.get("family_name", "").strip(),
            "given_name":  request.form.get("given_name", "").strip(),
            "institution": request.form.get("institution", "").strip(),
            "keyword":     request.form.get("keyword", "").strip(),
            "email":       request.form.get("email", "").strip(),
            "orcid_id":    request.form.get("orcid_id", "").strip(),
            "free_query":  request.form.get("free_query", "").strip(),
        }
        query_str = build_search_query(form_data)
        try:
            search_data = client.search(query_str, rows=25)
            total = search_data.get("num-found", 0)
            results = [
                {"orcid_id": (r.get("orcid-identifier") or {}).get("path", "")}
                for r in (search_data.get("result") or [])
            ]
        except requests.exceptions.HTTPError as e:
            error = f"Erreur API ORCID : {e.response.status_code} — {e.response.text[:200]}"
        except requests.exceptions.ConnectionError:
            error = f"Impossible de joindre l'API ORCID ({ENVIRONMENTS[get_env()]['label']})."
        except Exception as e:
            error = f"Erreur inattendue : {str(e)}"

    return render_template(
        "recherche.html",
        results=results, error=error, total=total,
        query_str=query_str, form_data=form_data,
    )


@app.route("/export-umontreal")
def export_umontreal():
    client = get_client()
    env_key = get_env()
    env_info = ENVIRONMENTS[env_key]

    try:
        orcid_ids = client.search_all("email:*@umontreal.ca", batch_size=100)
        if not orcid_ids:
            return Response("Aucun profil trouvé.", content_type="text/plain; charset=utf-8")

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "orcid_id", "orcid_url", "nom_complet", "prenom", "nom_famille",
            "courriels", "autres_noms", "pays", "identifiants_externes",
            "sites_web", "affiliations", "formations", "nb_publications"
        ])

        for oid in orcid_ids:
            try:
                person           = client.get_person(oid)
                works_data       = client.get_works(oid)
                employments_data = client.get_employments(oid)
                educations_data  = client.get_educations(oid)
                fundings_data    = client.get_fundings(oid)
                p = build_full_profile(oid, person, works_data,
                                       employments_data, educations_data,
                                       fundings_data, env_info)
                writer.writerow([
                    p["orcid_id"],
                    p["orcid_url"],
                    p["name"],
                    p["given_name"],
                    p["family_name"],
                    "; ".join(e["email"] for e in p["emails"]),
                    "; ".join(p["other_names"]),
                    "; ".join(a["country"] for a in p["addresses"]),
                    "; ".join(f"{i['type']}:{i['value']}" for i in p["external_identifiers"]),
                    "; ".join(u["url"] for u in p["researcher_urls"]),
                    " | ".join(
                        a["organization"] + (f" ({a['role']})" if a["role"] else "")
                        for a in p["affiliations"]
                    ),
                    " | ".join(
                        e["organization"] + (f" ({e['degree']})" if e["degree"] else "")
                        for e in p["educations"]
                    ),
                    p["works_count"],
                ])
                time.sleep(0.2)
            except Exception:
                writer.writerow([oid, f"{env_info['orcid_base']}/{oid}"] + [""] * 11)

        csv_content = output.getvalue()
        output.close()
        filename = f"orcid_umontreal_{env_key}.csv"
        return Response(
            csv_content,
            content_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        return Response(f"Erreur : {str(e)}", content_type="text/plain", status=500)


@app.route("/api/profil/<orcid_id>")
def api_profil(orcid_id: str):
    if not validate_orcid_id(orcid_id):
        return jsonify({"error": "Format ORCID invalide"}), 400
    try:
        return jsonify(get_client().get_record(orcid_id))
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": str(e)}), e.response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("🌐 ORCID Explorer v2 — http://localhost:5000")
    print("   Environnement par défaut : SANDBOX")
    app.run(debug=True, port=5000)
