import copy
from collections import OrderedDict

from usaspending_api.awards.v2.data_layer.orm_mappers import (
    FABS_AWARD_FIELDS,
    FPDS_CONTRACT_FIELDS,
    OFFICER_FIELDS,
    FPDS_AWARD_FIELDS,
    FABS_ASSISTANCE_FIELDS,
)
from usaspending_api.awards.models import Award, TransactionFABS, TransactionFPDS, ParentAward
from usaspending_api.recipient.models import RecipientLookup
from usaspending_api.references.models import Agency, LegalEntity, LegalEntityOfficers, Cfda
from usaspending_api.awards.v2.data_layer.orm_utils import delete_keys_from_dict, split_mapper_into_qs


def construct_assistance_response(requested_award_dict):
    """
        Build the Python object to return FABS Award summary or meta-data via the API

        parameter(s): `requested_award` either award.id (int) or generated_unique_award_id (str)
        returns: an OrderedDict
    """

    response = OrderedDict()
    award = fetch_award_details(requested_award_dict, FABS_AWARD_FIELDS)
    if not award:
        return None
    response.update(award)

    transaction = fetch_fabs_details_by_pk(award["_trx"], FABS_ASSISTANCE_FIELDS)

    cfda_info = fetch_cfda_details_using_cfda_number(transaction["cfda_number"])
    response["cfda_number"] = transaction["cfda_number"]
    response["cfda_title"] = transaction["cfda_title"]
    response["cfda_objectives"] = cfda_info.get("objectives")

    response["funding_agency"] = fetch_agency_details(response["_funding_agency"])
    response["awarding_agency"] = fetch_agency_details(response["_awarding_agency"])
    response["period_of_performance"] = OrderedDict(
        [
            ("period_of_performance_start_date", award["_start_date"]),
            ("period_of_performance_current_end_date", award["_end_date"]),
        ]
    )
    transaction["_lei"] = award["_lei"]
    response["recipient"] = create_recipient_object(transaction)
    response["place_of_performance"] = create_place_of_performance_object(transaction)

    return delete_keys_from_dict(response)


def construct_contract_response(requested_award_dict):
    """
        Build the Python object to return FPDS Award summary or meta-data via the API

        parameter(s): `requested_award` either award.id (int) or generated_unique_award_id (str)
        returns: an OrderedDict
    """

    response = OrderedDict()
    award = fetch_award_details(requested_award_dict, FPDS_AWARD_FIELDS)
    if not award:
        return None
    response.update(award)

    response["executive_details"] = fetch_officers_by_legal_entity_id(award["_lei"])
    response["latest_transaction_contract_data"] = fetch_fpds_details_by_pk(award["_trx"], FPDS_CONTRACT_FIELDS)
    response["funding_agency"] = fetch_agency_details(response["_funding_agency"])
    response["awarding_agency"] = fetch_agency_details(response["_awarding_agency"])
    response["period_of_performance"] = OrderedDict(
        [
            ("period_of_performance_start_date", award["_start_date"]),
            ("period_of_performance_current_end_date", award["_end_date"]),
        ]
    )
    response["latest_transaction_contract_data"]["_lei"] = award["_lei"]
    response["recipient"] = create_recipient_object(response["latest_transaction_contract_data"])
    response["place_of_performance"] = create_place_of_performance_object(response["latest_transaction_contract_data"])

    return delete_keys_from_dict(response)


def construct_idv_response(requested_award_dict):
    """
        Build the Python object to return FPDS IDV summary or meta-data via the API

        parameter(s): `requested_award` either award.id (int) or generated_unique_award_id (str)
        returns: an OrderedDict
    """

    idv_specific_award_fields = OrderedDict(
        [
            ("period_of_performance_star", "_start_date"),
            ("last_modified", "_last_modified_date"),
            ("ordering_period_end_date", "_end_date"),
        ]
    )

    mapper = copy.deepcopy(FPDS_CONTRACT_FIELDS)
    mapper.update(idv_specific_award_fields)

    response = OrderedDict()
    award = fetch_award_details(requested_award_dict, FPDS_AWARD_FIELDS)
    if not award:
        return None
    response.update(award)

    parent_award = fetch_parent_award_details(award["generated_unique_award_id"])
    response["parent_award"] = parent_award
    response["parent_generated_unique_award_id"] = parent_award["generated_unique_award_id"] if parent_award else None
    response["executive_details"] = fetch_officers_by_legal_entity_id(award["_lei"])
    response["latest_transaction_contract_data"] = fetch_fpds_details_by_pk(award["_trx"], mapper)
    response["funding_agency"] = fetch_agency_details(response["_funding_agency"])
    response["awarding_agency"] = fetch_agency_details(response["_awarding_agency"])
    response["idv_dates"] = OrderedDict(
        [
            ("start_date", award["_start_date"]),
            ("last_modified_date", response["latest_transaction_contract_data"]["_last_modified_date"]),
            ("end_date", response["latest_transaction_contract_data"]["_end_date"]),
        ]
    )
    response["latest_transaction_contract_data"]["_lei"] = award["_lei"]
    response["recipient"] = create_recipient_object(response["latest_transaction_contract_data"])
    response["place_of_performance"] = create_place_of_performance_object(response["latest_transaction_contract_data"])

    return delete_keys_from_dict(response)


def create_recipient_object(db_row_dict):
    return OrderedDict(
        [
            (
                "recipient_hash",
                fetch_recipient_hash_using_name_and_duns(
                    db_row_dict["_recipient_name"], db_row_dict["_recipient_unique_id"]
                ),
            ),
            ("recipient_name", db_row_dict["_recipient_name"]),
            ("recipient_unique_id", db_row_dict["_recipient_unique_id"]),
            ("parent_recipient_unique_id", db_row_dict["_parent_recipient_unique_id"]),
            ("parent_recipient_name", db_row_dict["_parent_recipient_name"]),
            ("business_categories", fetch_business_categories_by_legal_entity_id(db_row_dict["_lei"])),
            (
                "location",
                OrderedDict(
                    [
                        ("location_country_code", db_row_dict["_rl_location_country_code"]),
                        ("country_name", db_row_dict["_rl_country_name"]),
                        ("state_code", db_row_dict["_rl_state_code"]),
                        ("city_name", db_row_dict["_rl_city_name"]),
                        ("county_name", db_row_dict["_rl_county_name"]),
                        ("address_line1", db_row_dict["_rl_address_line1"]),
                        ("address_line2", db_row_dict["_rl_address_line2"]),
                        ("address_line3", db_row_dict["_rl_address_line3"]),
                        ("congressional_code", db_row_dict["_rl_congressional_code"]),
                        ("zip4", db_row_dict["_rl_zip4"]),
                        ("zip5", db_row_dict["_rl_zip5"]),
                        ("foreign_postal_code", db_row_dict.get("_rl_foreign_postal_code")),
                        ("foreign_province", db_row_dict.get("_rl_foreign_province")),
                    ]
                ),
            ),
        ]
    )


def create_place_of_performance_object(db_row_dict):
    return OrderedDict(
        [
            ("location_country_code", db_row_dict["_pop_location_country_code"]),
            ("country_name", db_row_dict["_pop_country_name"]),
            ("county_name", db_row_dict["_pop_county_name"]),
            ("city_name", db_row_dict["_pop_city_name"]),
            ("state_code", db_row_dict["_pop_state_code"]),
            ("congressional_code", db_row_dict["_pop_congressional_code"]),
            ("zip4", db_row_dict["_pop_zip4"]),
            ("zip5", db_row_dict["_pop_zip5"]),
            ("address_line1", None),
            ("address_line2", None),
            ("address_line3", None),
            ("foreign_province", db_row_dict.get("_pop_foreign_province")),
            ("foreign_postal_code", None),
        ]
    )


def fetch_award_details(filter_q, mapper_fields):
    vals, ann = split_mapper_into_qs(mapper_fields)
    return Award.objects.filter(**filter_q).values(*vals).annotate(**ann).first()


def fetch_parent_award_details(guai):
    parent_award_ids = (
        ParentAward.objects.filter(generated_unique_award_id=guai)
        .values("parent_award__award_id", "parent_award__generated_unique_award_id")
        .first()
    )

    if not parent_award_ids:
        return None

    parent_award = (
        Award.objects.filter(id=parent_award_ids["parent_award__award_id"])
        .values(
            "latest_transaction__contract_data__agency_id",
            "latest_transaction__contract_data__idv_type_description",
            "latest_transaction__contract_data__multiple_or_single_aw_desc",
            "latest_transaction__contract_data__piid",
            "latest_transaction__contract_data__type_of_idc_description",
        )
        .first()
    )

    parent_object = OrderedDict(
        [
            ("agency_id", parent_award["latest_transaction__contract_data__agency_id"]),
            ("award_id", parent_award_ids["parent_award__award_id"]),
            ("generated_unique_award_id", parent_award_ids["parent_award__generated_unique_award_id"]),
            ("idv_type_description", parent_award["latest_transaction__contract_data__idv_type_description"]),
            (
                "multiple_or_single_aw_desc",
                parent_award["latest_transaction__contract_data__multiple_or_single_aw_desc"],
            ),
            ("piid", parent_award["latest_transaction__contract_data__piid"]),
            ("type_of_idc_description", parent_award["latest_transaction__contract_data__type_of_idc_description"]),
        ]
    )

    return parent_object


def fetch_fabs_details_by_pk(primary_key, mapper):
    vals, ann = split_mapper_into_qs(mapper)
    return TransactionFABS.objects.filter(pk=primary_key).values(*vals).annotate(**ann).first()


def fetch_fpds_details_by_pk(primary_key, mapper):
    vals, ann = split_mapper_into_qs(mapper)
    return TransactionFPDS.objects.filter(pk=primary_key).values(*vals).annotate(**ann).first()


def fetch_agency_details(agency_id):
    values = [
        "toptier_agency__fpds_code",
        "toptier_agency__name",
        "toptier_agency__abbreviation",
        "subtier_agency__subtier_code",
        "subtier_agency__name",
        "subtier_agency__abbreviation",
        "office_agency__name",
    ]
    agency = Agency.objects.filter(pk=agency_id).values(*values).first()

    agency_details = None
    if agency:
        agency_details = {
            "id": agency_id,
            "toptier_agency": {
                "name": agency["toptier_agency__name"],
                "code": agency["toptier_agency__fpds_code"],
                "abbreviation": agency["toptier_agency__abbreviation"],
            },
            "subtier_agency": {
                "name": agency["subtier_agency__name"],
                "code": agency["subtier_agency__subtier_code"],
                "abbreviation": agency["subtier_agency__abbreviation"],
            },
            "office_agency_name": agency["office_agency__name"],
        }
    return agency_details


def fetch_business_categories_by_legal_entity_id(legal_entity_id):
    le = LegalEntity.objects.filter(pk=legal_entity_id).values("business_categories").first()

    if le:
        return le["business_categories"]
    return []


def fetch_officers_by_legal_entity_id(legal_entity_id):
    officer_info = LegalEntityOfficers.objects.filter(pk=legal_entity_id).values(*OFFICER_FIELDS.keys()).first()

    officers = []
    if officer_info:
        for x in range(1, 6):
            officers.append(
                {
                    "name": officer_info["officer_{}_name".format(x)],
                    "amount": officer_info["officer_{}_amount".format(x)],
                }
            )

    return {"officers": officers}


def fetch_recipient_hash_using_name_and_duns(recipient_name, recipient_unique_id):
    recipient = None
    if recipient_unique_id:
        recipient = RecipientLookup.objects.filter(duns=recipient_unique_id).values("recipient_hash").first()

    if not recipient:
        # SQL: MD5(UPPER(CONCAT(awardee_or_recipient_uniqu, legal_business_name)))::uuid
        import hashlib
        import uuid

        h = hashlib.md5("{}{}".format(recipient_unique_id, recipient_name).upper().encode("utf-8")).hexdigest()
        return str(uuid.UUID(h))
    return recipient["recipient_hash"]


def fetch_cfda_details_using_cfda_number(cfda):
    c = Cfda.objects.filter(program_number=cfda).values("program_title", "objectives").first()
    if not c:
        return {}
    return c
