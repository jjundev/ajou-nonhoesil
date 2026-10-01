# Experiment 04 independent acceptance review

## Blind phase (written before opening problems/*.html or supplied solutions)
Reviewed all 12 blind HTML prompts, all 8 section HTML fragments, and prompt-only source crops s07-p1-o-s07-q5, s03-p1-o-s03-q2, s03-p1-o-s03-q3. This phase did not read the problem solution/original panels. The parent task disclosed known conflict categories beforehand; derivations below follow the prompt conditions and circuit logic.

1. q-active-general: Active high means assertion/function enabled at logical 1, active low means assertion/function enabled at logical 0. Neither label alone determines the carried data value or disabled output value.
2. q-decoder: With active-high decoded address terms C0=S1′S0′, C1=S1′S0, C2=S1S0′, C3=S1S0, MUX forms Y=sum(Ck Ik), while DMUX forms separate Yk=D Ck. D=1 makes the latter a decoder. n selectors distinguish 2^n paths; total input count must not be confused with data-line count.
3. q-demux2: Invert S once; AND D with S′ for Y0 and D with S for Y1. For (S,D)=00,01,10,11, (Y0,Y1)=00,10,00,01. No OR gate.
4. q-demux4: Under the AND-based ideal circuit, D=0 gives Y3 Y2 Y1 Y0=0000 independently of S. At D=+5V (logical 1), addresses 00,01,10,11 give 0001,0010,0100,1000. The prompt omits the original circuit image, but the linked notes specify the ideal model and disclose the original X row. Source X cannot be independently interpreted as Z or a measured unknown.
5. q-demuxdef: One data input is sent to one of several outputs selected by address lines. For the active-high AND model, unselected outputs are 0.
6. q-design4: Two NOT gates generate S1′,S0′. Four three-input AND gates produce S1′S0′I0, S1′S0 I1, S1 S0′I2, S1 S0 I3. Their four-input OR is Y. The prompt crop contains only the given truth/function table and block diagram, with no worked answer.
7. q-difference: MUX chooses one of N input data signals for one output; DMUX routes one input data signal to one of N outputs. Both use selector address signals.
8. q-mux2-graded: Y=Sel′X0+Sel X1. In the given four-row order outputs are 0,1,1,1. NOT Sel, two AND branches, then OR. The provided four rows are only the requested subset, not the exhaustive eight-input-combination table.
9. q-mux2: Y=S′I0+SI1. For rows (S,I0,I1)=000,001,010,011,100,101,110,111, Y=0,0,1,1,0,1,0,1.
10. q-mux4: The source crop has active-low E implemented by NOT into the gated NAND terms. All rows E=0 are enabled. S1S0 selects D0,D1,D2,D3; the printed column order is D3,D2,D1,D0. Values selected by the four rows are 0,1,0,0. E=1 makes each first-layer NAND output 1, so final NAND output is 0.
11. q-muxdef: A selector-controlled combinational circuit passes one chosen input to its single output; n selector bits distinguish up to 2^n inputs.
12. q-tri: Given nOE=0 enables and nOE=1 gives Z. For convention S=0 chooses I0 and S=1 chooses I1, connect nOE0=S, nOE1=S′, data I0/I1 to respective A pins and the B outputs together as Y. S=0 gives I0/Z, S=1 gives Z/I1. The active-high implementation would reverse the enable wiring; it is not transferable unchanged. Z is not 0.

## Blind note sufficiency
The notes independently supply the gate meanings, truth-table reading, selector bit weights, Boolean formulas, complete base truth tables, enable polarity, X/Z distinction, gate count/connections, and tri-state conditions needed for every prompt. MUX has a worked example plus a partial-step exercise. DMUX and decoder explanations can support the remaining derivations without supplied solutions. The sequence is suitable for a learner returning to logic. Minor polish: an explicit paired one-sentence active-high/active-low definition would make q-active-general less dependent on inference from buffer/decoder examples. Source X conflicts are already honestly disclosed in the notes; notes are allowed to teach the answer and are not claimed to be a blind examination.

## Post-blind comparison
Pending; this section will be appended after solutions and provenance are reviewed.

## Final comparison and findings (2026-10-01)

### Important — P1: Korean learning pack contains substantial Japanese author prose
At the reviewed revision, problems/q-active-general.html:1, q-demux2.html:1, q-demux4.html:1, q-design4.html:1, and q-mux2-graded.html:1 contain Japanese solution/explanation/check prose. manifest.json also supplies Japanese titles for q-demux2, q-design4, q-mux2-graded and q-active-general, and Japanese inclusion/holding reasons. These are learner-facing author text, not preserved foreign-language source quotations. A Korean learner cannot reliably use several explanations. Translate the authored titles, prose, table headings/alt text, derived-answer description and audit reasons into Korean before publication; preserve immutable bank/evidence and mathematical conditions. This is an educational acceptance blocker. Correctness of equations alone does not resolve it.

### Minor — P3: Add a paired definition of active high/low to the notes
sections/t-mux4.html clearly defines active low. Active high is inferable from the buffer/decoder examples, but q-active-general asks both explicitly. A short paired Korean definition in the concept note would remove an avoidable inference for a returning learner. The distinction between asserted control and resulting data/output is otherwise explained well.

No other critical/important error was found in the content reviewed. A single fresh review was performed; no project files were edited by this reviewer. This report is not a post-fix acceptance certificate.

### What matched the independent derivations
- All 12 solutions and their tables/formulas match the blind derivations above, under the conditions explicitly taught. q-mux4 gives 0,1,0,0; q-mux2-graded gives 0,1,1,1.
- q-tri retains answer_status=disputed and explains why the active-high candidate cannot be copied to the nOE=0 source conditions. The original candidate caption was visually confirmed in evidence/assets/s06-p4.png.
- q-demux4 retains answer_status=disputed, shows ideal AND results and preserves the source D=0/X row as source evidence. It does not claim those ideal results are measured values. Original s04-p1 and manual p12 contain the X row; manual p11 supports the ideal 0000 result.
- Manual p8 NAND schematic independently gives active-low E and disabled Y=0; manual p9 prints X for disabled output. Notes make this distinction explicitly. Manual p11 uses separate AND outputs, consistent with the equations and absence of an output OR.
- The graded four-row input table exactly matches the printed source crop s05-p1-q2.png. The worked general eight-row table remains separately available.
- Manifest count is 7 past + 3 unknown + 2 selected predicted = 12 included; held q-active/q-switch/q-empty-six = 3. No held item is silently represented as solved. The two selected predicted tasks fill gate-design practice gaps.
- The local current manual cover was text-read via pypdf and says 25-1. The pack discloses that cover versus 2026-2 distribution. The September 14 notice was directly read and supports experiment 4 items 1-1 and 2-1. Distribution provenance itself was inherited from the provided repository context, not independently retrieved online.
- All problem fragments have a collapsed original-evidence panel; answer-bearing original images are absent from the blind problem regions. The three directly visible source crops q-mux4/q-tri/q-design4 were visually inspected and show given conditions, not completed solutions. No answer exposure was found in those visible prompts, their alt text or generic hints. The detailed notes appropriately contain teaching answers. Browser open/closed behavior remains the parent's responsibility.

### Source inspection scope
Visually inspected: manual-8/9/11/12; s03-p1-o-s03-q1/q2/q3/q4; s05-p1-q1/q2/q3; s07-p1-o-s07-q4/q5; s04-p1; s06-p4. Also inspected s08-p2 and s07-p2-o-s07-q6 (switch illustration). Read manifest, q-tri bank question/answer occurrence records, authoring/verification skill references, and Task 8/C1-C3 plan text. This is not a fresh re-extraction audit of every historical source page or all duplicate locations.

### Code and checks
Reviewed the single html2md.py change that prefixes list-item output with its existing anchor, and the new held-list-item regression. This directly preserves the MD target for held-question links and does not change prose/table rendering. Ran `python -m pytest -n0 -p no:cacheprovider tests/test_review_pack_md.py -q` with bytecode disabled: **6 passed**. No implementation-level defect found in this small change.

Independently enumerated all 128 E/S1/S0/D0..D3 combinations for the NAND 4:1 implementation against `(1-E)*D[2*S1+S0]`: pass. Enumerated all 8 D/S1/S0 combinations for ideal AND DMUX: pass.

C1 reasoning check: absent initial Q, the output before the first relevant rising edge is unknown; D=1 at the first rising edge establishes Q=1. No Q=0 assumption is allowed.
C2 reasoning check: active-low enable at 1 disables the function, but the disabled output requires actual device/circuit conditions. For this pack, the NAND schematic supplies those conditions and gives 0; generic MUX selection formula alone would not suffice.
C3 independent unit calculation: the explicitly given P=CV²f with 10 pF, 5 V and 1 MHz yields 10×10^-12×25×10^6=250×10^-6 W=250 µW. This is a check of the given model, not a claim of a universal power formula.

### Limitations and disposition
**Acceptance requires correcting the P1 Japanese author text and checking the rebuilt outputs.** The mathematical/source-condition review otherwise supports the reviewed content. Browser layouts, interaction, print, network isolation, rebuilt MD/HTML equality, source hashes at publication, final-folder links and publication are not certified by this reviewer. Current manifest checks were still not_run when read; the parent must record only checks actually completed against the final rebuilt stage.
