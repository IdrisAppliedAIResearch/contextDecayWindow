# ACTIVE: confirmation stopped at output cap; authorization pending

2026-09-06: reader stopped after456/3508physicalcalls. Lastresponse endedstop_type=limit,tokens_predicted8192,truncatedfalse.455EOS incl3calibration,452measurementEOS;3052originalcallsunissued. No uncertainjournal. Rawarchive andstop_audit committed98bf6e14. No correctness orconfirmationtracesopened. Dedicatedserver20516 stopped afterverifiedidentity. DO NOT rerunreader_confirmation.py orscoreincompletepopulation.

CONFIRMATION_STOP_REPORT.md iscurrentstatus. Amendment004_output_cap_continuation_DRAFT.md isconcreteproposalforonecommon16384capcontinuation withstrictcalibration/prefixidentitychecks,alloriginalidentitiesretained. It isDRAFT, requiresuserauthorizationbecause lockedregistrationprohibitsautomaticcapincrease. No continuationcode/callswritten. Monitoringpausedpendingdecision. SameStudyE/PR95, notnewstudy. Ifuserapproves: commitauthorizedamendmentdesign-onlybeforeimplementation, preserveoriginals, implementexactproposal,gates andboundedstop. Do notinferapprovalfromelapsedtime.

Prior running/preparation contextbelowishistorical; currentheadergoverns.

---

# ACTIVE: Study E confirmation reader running

Reader session64499; dedicated serverPID20516 on8097. Registered confirmation inputs completed and committed2c781515. Runtime/tokenizer/compact schedules and scorer sealed92cb3a3d. check_run passed; maximum input12042tokens; prefix and short calibration passed (3/3508). There are3840logicalanswers and3508physicalcalls including3calibration. Reader_confirmation.py run is already active; do not start again or poll healthy progress.

Terminal artifacts: artifacts/confirmation/reader/complete.json or failure.json. Healthy fsynced responses.jsonl is intentionally ignored inGit. On PASS the runner creates lossless responses.jsonl.gz and complete hashes. Verify process identity before stopping only20516. Commitcomplete,prefix,gzip,fullserverlogs before scoring. Never open confirmationanswer content or traces early. Anyfailure/uncertainjournal: preserve and reportinstrumentstop, no retries/capchange. Quiet completion/failure hooks own ongoing work.

Postcompletion code now exists: score_confirmation.py verifiescommittedgzip andcompleteness, emits3840blindlogicalrows, frozenmechanicalscores,mapping and unique pending groups. Force-addpending_adjudication.json (ignored pattern); commitallscores/surface/mapping beforemanualreview. Calibrateagain on frozenAmend003RATER_CALIBRATION beforeopeninganswers. Manualblindreviewunderregisteredagent-onlyauthorization: write batches under reader/adjudications/*.json, eachrow review_key,score,evidence,rationale,corrected_wrong_opening boolean. Reviewkeygroups identicalquestion/ref/response; preserve alllogicalscoreIDs. Noarms/source/historyshown inpacket. Do notaskagainforauthorizedagent review. Genuinecriterionambiguityblocks unseal.

Commit alladjudicationbatches. resolve_confirmation.py requirescommittedbatches, exactcoverage andno conflicts; writesimmutable scores_resolved/newgate. Committhese BEFORE analyze_confirmation.py, whichopensmapping andtraces andcomputesregistered group-leveldecision/CI/guards pluscorrectness×exactevidence. The analyzer'sthresholdsuseexactcountfractions, avoiding floatthresholdrounding; positive/signal/tie/eachharmfixtures passed. Still complete registered descriptive diagnostics in finalreport: candidate/temporal/final carrier survival andranks/costs/displacement, referencearms andconditional comparisonsdescriptive only. Do notreinterpret bar orretune.

Older preparation context below is historical; the currentheadergoverns stage. Confirmationgenerator/data/reference artifacts remainfrozen. No confirmationoutcomesopened. Useraskedquiet hooks. UpdateREADME/AGENTS<=400/memory/PR95 onterminalmeaningfulchanges; no merge/deploy/adoption.

---

# Study E: registered confirmation preparation

Current stage: confirmation inputs being prepared. User authorized end-to-end work, agent scoring and same-study amendments. Continue Study E on study/E-before-ordering, PR95; no new study. Read PRE_REGISTRATION.md, which governs all future confirmation work. Registration design-only SHA2e047c41c80748b16f0e6df15dcc70ac54145598. No confirmation outcome has been opened.

Amendment003 reader COMPLETE:43calls, finalbefore C0=3/12,C1=6/12,4gains1loss7ties. Latest3/4each byteidentical; absence4/4each. Exact evidence onreader12:3->10; C1completewrong4. Offline16:4->13,9gains0losses. Thirteen authorizedagent exceptions, nohuman audit. Scores5ad31974 committed beforeaggregate4c28e643. Reader server9544 STOPPED. AMENDMENT_003_REPORT.md owns this result. OriginalpilotREPORT.md historical11/12tie. SharedlogsAmend002 stoppedoffline. Originaltext-onlyAmend003rows/gate INVALID, exact versions authoritative.

RUNNING: .venv/Scripts/python.exe experiments/study_E/prepare_confirmation.py, unifiedsession92869. This is CPU embedding/preparation, not reader inference. Outputs artifacts/confirmation/development_inputs/complete.json or failure.json. 32groups seeds94001-94032,192histories,26880records; eachhistory140records. Eightworkers, expected~17minutes based prior125seconds for4groups. Sourcefile can remain unchanged throughoutembedding; do not falsely call that a stall while workers accumulateCPU. Quiet monitor; no healthy polling. Technicalfailure preserves artifacts; no overwrite/reseed.

Preparation implementationd673f710 verifies registration-onlycommit, generator/mechanism/modelSHAs, Python3.13.13/NumPy2.4.6, cleancontrols05ef90e2+5ebda1ef, exactregenerationof24devhistories. Sourcegold parsed; allrequired<109. EmbeddingssingletextoneCPUthreadx8 andsentinelidentical. Fulltokens/promptstore follows. traces_sealed.json contains confirmationmechanism/evidence outcomes: do NOT open or aggregate untilallscorescommitted. Inputgate may mechanicallyinspectinvariants, no benefitfilter.

On preparation terminalPASS: commit allnewinputartifacts includingsealedtraces withoutopeningtraces. Confirm complete/manifest/hashcounts. Start dedicated sameQwenserver on8097 only after verifying portfree, using exact command from artifacts/amendment003/reader/launch.json and CUDAchildPATH v13.2/bin/x64+v12.6/bin. Use Start-Process -WindowStyle Hidden and new logs under artifacts/confirmation/reader; capturePID/command/loadedruntime. Logs remainuntrackeduntilterminal to avoidmodifying committedartifacts.

Reader code reader_confirmation.py implements seal/run. Afterserverready, run seal; it hashesruntime, tokenizesalluniqueprompts, validatesallowance, createscompactprompt_store/logical_schedule/physical_schedule/input_gate. Same3840logicalanswers butfullprompt+seedaliases reducephysicalcalls; threecalibrationcallsadded. Commit runner andinputgate/schedules/promptstore/props/launch BEFORE run. Run check_run negative/positiveverification and actualrun onlyaftersealcommit. Registeredcap8192; nslots1; sameHH001emptythink. No explanationsrequested. Source/vector hashes andcontrolsclean mustpass. No inferencebeforecommittedgate.

Run reader_confirmation.py run in backgroundexec. It fsyncs everyresponse and pendingjournal; anyuncertaincall stops, no retry. Prefixidentical required. Atfullcompletion it creates exact gziparchive andcomplete.json. Raw responses.jsonl is ignored to avoidGitHubsize limit; gzipis losslessrawrecord withverifiedSHA. Onfailurepreservealloutputs/journal, recordinstrumentstop notmechanismfailure. Updateheartbeatprompt/thishandoff withactualsession/PID/stage. Stop onlyverifieddedicatedserverafterterminal. Commitcomplete+gzip+logs before scoring.

Confirmation scorer/analyzer STILL TO IMPLEMENT afterreading registeredrules. Can use score_amendment003.py grammar asreference, but confirmationresponses storephysicalIDs and logicalaliases, notfullquestionrows. Verify gziprawhash andall3840logical mappings. Makeblindlogicalsurface opaqueIDs withquery/ref/response, noarms/history/source. CalibrationAmend003RATER_CALIBRATION frozen. Mechanical scores then singleagentexceptionjudgments underprospective registration, withrationales/exactfinalanswer andcorrectedwrongopeningflags. Preservependingfiles; allresolvedscores committedBEFORE openingarmmapping ortraces. No human/independentpass claim. Do not ask againforalready authorizedagent scoring. Genuineunresolvedrubricquestion blocksunseal.

Analysis:32groupunits,5seedmeansx4conditions; fixedD1/D2/harms fromPRE_REGISTRATION. Signflip100000seed95001,bootstrap10000seed95002; guardprecedence. Referencearms and exactevidencecorrect/wrong tables. prelock_checks.py reachablefixtures_v2 valid; oldprelock.json .5perquestioninvalidsuperseded. No confirmationtreatmentbenefitgate. No adopting baseddevelopment.

UpdateREADME/AGENTS<=400/memory/status/PR95 withactualstage. Keepquietunchangedhealthy. No merge/deploy. Ifconfirmationrunslong, heartbeatcontinuationdefault; useraskedhooksratherthanpolling.
