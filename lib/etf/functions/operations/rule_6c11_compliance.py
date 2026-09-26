"""Custom-basket operational review records, not a Rule 6c-11 legal certification.

The rule permits nonrepresentative baskets under adopted policies and designated
review. Numeric overlap/deviation limits, if used, are internal policy parameters.
See https://www.ecfr.gov/current/title-17/section-270.6c-11.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from uuid import uuid4


@dataclass
class Rule6c11Validation:
    passed: bool
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    validation_details: dict = field(default_factory=dict)


class Rule6c11Compliance:
    """Historical API name; passed means documented internal checks only."""
    def __init__(self, storage_path='./data/compliance', policy_thresholds=None):
        self.storage_path=Path(storage_path)
        self.storage_path.mkdir(parents=True,exist_ok=True)
        self.policy_thresholds=policy_thresholds or {}

    def validate_custom_basket(self, standard_basket, custom_basket, pcf_total_value, *, review=None):
        errors=[]
        details={'legal_compliance':'not_determined','review_status':'pending',
                 'internal_policy_thresholds':self.policy_thresholds}
        try:
            total=Decimal(str(pcf_total_value))
            if not total.is_finite() or total<=0:raise ValueError('Positive finite PCF total required')
            if not custom_basket:raise ValueError('Custom basket is empty')
            identifiers=set()
            value=Decimal(0)
            for holding in custom_basket:
                identifier=holding.get('cusip') or holding.get('identifier')
                if not identifier or identifier in identifiers:raise ValueError('Missing or duplicate security identifier')
                identifiers.add(identifier)
                quantity=Decimal(str(holding['quantity'])); price=Decimal(str(holding['price']))
                if not quantity.is_finite() or not price.is_finite() or quantity<0 or price<=0:
                    raise ValueError('Quantities/prices must be finite with nonnegative quantity and positive price')
                value+=quantity*price
            standard={h.get('cusip') or h.get('identifier') for h in standard_basket}
            standard.discard(None)
            overlap=Decimal(len(identifiers&standard))/Decimal(len(standard)) if standard else None
            deviation=abs(value-total)/total
            details.update(cusip_overlap=float(overlap) if overlap is not None else None,
                           value_deviation=float(deviation),custom_total_value=str(value))
            if 'minimum_overlap' in self.policy_thresholds and (overlap is None or overlap<Decimal(str(self.policy_thresholds['minimum_overlap']))):
                errors.append('Below configured internal overlap threshold; not a statutory numeric test')
            if 'maximum_value_deviation' in self.policy_thresholds and deviation>Decimal(str(self.policy_thresholds['maximum_value_deviation'])):
                errors.append('Exceeds configured internal value-deviation threshold; not a statutory numeric test')
        except (ValueError,ArithmeticError,KeyError) as exc:
            errors.append(str(exc))
        required=('policy_version','designated_reviewer','reviewed_at','purpose','ap_id','cash_balancing_amount')
        review=review or {}
        missing=[key for key in required if key not in review or review[key] is None or str(review[key]).strip()=='']
        if missing:errors.append('Missing review evidence: '+', '.join(missing))
        else:
            try:
                reviewed=datetime.fromisoformat(review['reviewed_at'].replace('Z','+00:00'))
                cash=Decimal(str(review['cash_balancing_amount']))
                if reviewed.tzinfo is None or not cash.is_finite():raise ValueError('Timezone-aware review time and finite cash amount required')
            except (ValueError,ArithmeticError,TypeError) as exc:errors.append(str(exc))
        if review.get('approved_under_adopted_policy') is not True:
            errors.append('Designated review under the adopted policy has not been recorded')
        details.update(review_evidence=review,review_status='recorded' if not errors else 'pending')
        result=Rule6c11Validation(not errors,errors,['Evidence is supplied by the caller; this code does not establish legal compliance.'],details)
        self._save_validation_record(result,standard_basket,custom_basket)
        return result

    def validate_custom_basket_purpose(self, custom_basket, standard_basket, purpose):
        """Check presence of a documented purpose, not its legal acceptability."""
        return bool(isinstance(purpose,str) and purpose.strip())

    def generate_custom_basket_disclosure(self, custom_basket, standard_basket, validation):
        record={'record_type':'internal_basket_review','created_at':datetime.now(timezone.utc).isoformat(),
                'custom_basket':custom_basket,'standard_basket':standard_basket,
                'validation_result':asdict(validation),'legal_compliance':'not_determined',
                'required_follow_up':['Confirm adopted custom-basket parameters and deviation process.',
                                      'Retain the designated review, AP identity, balancing cash and basket records.',
                                      'Apply the actual record retention and AP agreement requirements.']}
        self._write('basket_review',record)
        return record

    def _write(self,prefix,record):
        target=self.storage_path/f'{prefix}_{uuid4().hex}.json'
        with target.open('x') as handle:json.dump(record,handle,indent=2,default=str)

    def _save_validation_record(self,validation,standard_basket,custom_basket):
        self._write('basket_validation',dict(validation=asdict(validation),standard_basket=standard_basket,custom_basket=custom_basket))
