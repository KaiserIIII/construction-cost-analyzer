# Development input review

## Purpose

Add a local preflight command to the existing development engine. An arithmetically valid estimate may still rely on missing costs defaulted to zero or undocumented sales assumptions. The review must distinguish those gaps from calculation errors, and must not claim independent verification, market validation, NRM certification or a predicted assessment mark.

## Selected scope

Extend the existing engine and exports rather than introduce a second calculator or a new user interface. A standalone `review` CLI command reads a saved development JSON. It uses the existing engine for numerical validation, reports explicit input omissions and evidence gaps by field path, records the adopted option programmes, and hashes the input snapshot. It returns a nonzero exit status for blocking gaps. Existing calculation commands keep their behavior.

Housing rows gain optional `sale_source_ref`, `sale_price_date` and `sale_basis` (`asking`, `sold`, `assumed`). These are retained in outputs. A general construction benchmark reference must not automatically become evidence of the selling price. The review never follows URLs or uploads files.

Required explicit costs: land, site clearance, facilitating, external works, preliminaries, OH&P, fees, marketing, four risks and two inflation allowances. Required programme/funding declarations: duration, preparation months/spend, start date, loan share and, when borrowing is positive, interest and arrangement fee. Option overrides satisfy their corresponding requirements. Both rate inclusion flags and the pricing/risk bases must be stated. Explicit zero is accepted; omission is reported.

Missing area/rate/index/sales references and price dates are blocking documentation gaps. An assumed selling price, asking-price evidence, a sales date after the estimate date and a net-rate reconstruction of preliminaries receive warnings. Recording a reference is not verification of its content. A documented-input status must never be called submission-ready.

## Delivery

Use standard-library Python only, preserve existing exports and all existing tests. Add independently expected boundary and CLI tests, plus a documented synthetic example. No student report, workbook, identity, private source or final project answer enters the repository. The classmate guide is a separate four-page basic how-to with an explicitly identified maintainer recommendation and no source bibliography. It explains the process while excluding the student's actual calculations and extended analysis.
