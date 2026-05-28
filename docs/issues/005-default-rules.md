# feat(rules): default rule corpus (20+ prompt injection, 10+ output policy)

**Labels:** enhancement

## Prompt Injection Rules (L5)

| ID | Category | Weight | Pattern |
|----|----------|--------|---------|
| `inj_override_ignore` | instruction_override | 0.9 | `ignore\s+(?:all\s+)?(?:previous\|prior)\s+(?:instructions?\|rules?\|prompts?)` |
| `inj_override_forget` | instruction_override | 0.85 | `forget\s+(?:all\s+)?(?:previous\|prior)\s+(?:instructions?\|rules?\|context)` |
| `inj_override_disregard` | instruction_override | 0.85 | `disregard\s+(?:all\s+)?(?:previous\|above)\s+(?:instructions?\|rules)` |
| `inj_role_dan` | role_manipulation | 0.95 | `you\s+are\s+(?:now\s+)?DAN\|DAN\s+mode` |
| `inj_role_act_as` | role_manipulation | 0.8 | `act\s+as\s+if\s+you\s+are\|pretend\s+(?:to\s+)?be\s+(?:a\|an)` |
| `inj_role_system` | role_manipulation | 0.9 | `(?:you\s+are\s+now\|switch\s+to)\s+(?:a\s+)?(?:system\|admin\|root)` |
| `inj_context_hidden` | context_injection | 0.7 | hidden instruction patterns in retrieved documents |
| `inj_context_append` | context_injection | 0.65 | `\[\[.*instructions?:.*\]\]\|<\!--.*-->'` |
| `inj_encode_base64` | encoding_attack | 0.75 | base64-decoded content containing instruction patterns |
| `inj_encode_rot13` | encoding_attack | 0.7 | ROT13-decoded instruction patterns |
| `inj_encode_url` | encoding_attack | 0.65 | URL-decoded instruction patterns |
| `inj_encode_hex` | encoding_attack | 0.65 | hex-decoded instruction patterns |
| `inj_extract_system` | extraction_attempt | 0.85 | `(?:repeat\|reveal\|show\|print\|output)\s+(?:your\|the)\s+(?:system\|initial)\s+(?:prompt\|instructions?)` |
| `inj_extract_rules` | extraction_attempt | 0.8 | `what\s+(?:are\s+)?(?:the\s+)?(?:rules\|instructions\|guidelines)\s+(?:were\s+)?you\s+(?:given\|told)` |
| `inj_extract_train` | extraction_attempt | 0.75 | `(?:training\s+data\|training\s+examples?\|corpus)` |
| `inj_multiturn_game` | multi_turn_trap | 0.6 | `let'?s\s+play\s+a\s+game\|for\s+(?:research\|academic\|educational)\s+purposes` |
| `inj_multiturn_bypass` | multi_turn_trap | 0.55 | `(?:hypothetically\|theoretically\|imagine\s+that)\s*,\s*(?:what\|how\|if)` |
| `inj_unicode_homoglyph` | encoding_attack | 0.7 | Unicode confusable characters that normalize to ASCII instruction words |
| `inj_zwnj` | encoding_attack | 0.65 | Zero-width non-joiner/joiner injection between instruction words |
| `inj_format_breakout` | instruction_override | 0.75 | `\}\]\s*(?:now\|ignore\|forget)\|```(?:sql\|python\|bash)\s*.*(?:rm\|DROP\|exec)` |

## Output Policy Rules (L6)

| ID | Category | Weight | Pattern |
|----|----------|--------|---------|
| `out_pii_ssn` | pii_leak | 0.95 | SSN pattern `\d{3}-\d{2}-\d{4}` |
| `out_pii_credit_card` | pii_leak | 0.95 | Credit card Luhn-valid patterns |
| `out_pii_email` | pii_leak | 0.8 | Email address pattern |
| `out_pii_phone` | pii_leak | 0.75 | Phone number patterns |
| `out_pii_api_key` | pii_leak | 0.9 | API key patterns (AWS, GCP, generic) |
| `out_harm_violence` | harmful_content | 0.85 | Violence/self-harm instruction indicators |
| `out_harm_csam` | harmful_content | 0.99 | CSAM content indicators |
| `out_harm_self_harm` | harmful_content | 0.9 | Self-harm instruction indicators |
| `out_exfil_env_var` | exfiltration | 0.85 | Environment variable patterns |
| `out_exfil_internal_url` | exfiltration | 0.75 | Internal URL patterns (10.x, 192.168.x, localhost) |

## Acceptance Criteria

- [ ] 20+ prompt injection rules with weights and normalization hints
- [ ] 10+ output policy rules
- [ ] All rules pass schema validation on load
- [ ] Corpus hash reproducible across loads
