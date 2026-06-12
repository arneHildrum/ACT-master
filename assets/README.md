# Power Technology Scale Factors

Constructs a power technology scaling model based on publicly available information.
Information on the relatively power scaling between processes and there are several variations across each process node.
It should also be noted that in reality the power will scale depending on the power composition between leakage, dynamic, memory, etc.
As a result, the accuracy of the scale factors projections here should be treated appropriately as a first order model which to illustrate carbon emissions trends should be sufficient.

For processes where scale factors are not publicly available, the power scaling at iso-performance is assumed conservatively to be 0.8.
We use TSMC processes to build the model so there are some technology nodes from other foundries which will lie outside the TSMC process geometries.
Since ascertaining the power scaling factors between different foundry processes is difficult, we assume that roughly equivalent generation technology processes have the scale scale factors (ex., TSMC16 = GF14).

Source data and assumptions for technology scaling factors:
* TSMC N65 -> TSMC N40: https://pr.tsmc.com/english/news/1526
* TSMC N45 -> TSMC N40: https://pr.tsmc.com/english/news/1526
* TSMC N40 -> TSMC N28: Assume 0.8 since no publicly available data
* TSMC N28 -> TSMC N20: https://semiwiki.com/forum/threads/tsmc-20nm-specifications-are-up.1732/#:~:text=Admin.%20TSMC's%2020nm%20process%20technology%20is%2030,tablets%20and%20smartphones%20to%20desktops%20and%20servers.
* TSMC N20 -> TSMC N16: https://www.tsmc.com/english/dedicatedFoundry/technology/logic/l_16_12nm#:~:text=TSMC's%2016/12nm%20processes%20provide,to%20TSMC's%2020nm%20SoC%20process.
* TSMC N16 -> N14: TSMC does not have a 14nm logic node. So approximate as roughly the same as TSMC16 even though this is technically not precise.
* TSMC N16 -> TSMC N7: https://en.wikichip.org/wiki/7_nm_lithography_process#:~:text=N7%5Bedit%5D%20TSMC%20original%207%2Dnanometer%20N7%20process%20was,~20%25%20speed%20improvement%20or%20~40%25%20power%20reduction.
* TSMC N10 -> TSMC N7: https://en.wikichip.org/wiki/7_nm_lithography_process#:~:text=N7%5Bedit%5D%20TSMC%20original%207%2Dnanometer%20N7%20process%20was,~20%25%20speed%20improvement%20or%20~40%25%20power%20reduction.
* TSMC7 -> N8: TSMC does not have a 8nm logic node. So approximate as roughly the same as TSMC7 even though this is technically not precise.
* TSMC7 -> TSMC7_EUV: Assume a conservative improvement based on the article of 0.85 - https://pr.tsmc.com/english/news/2010
* TSMC N7 -> TSMC N5: https://www.tomshardware.com/news/tsmc-5nm-4nm-3nm-process-node-introduces-3dfabric-technology#:~:text=TSMC's%205nm%20'N5'%20process%20employs,rates%20quicker%20than%20its%20predecessor.
* TSMC N5 -> TSMC N3: https://www.tsmc.com/english/dedicatedFoundry/technology/platform_smartphone_tech_advancedTech#:~:text=N3E%20is%20an%20optimized%203nm,an%20optical%20shrink%20of%20N3E.
* TSMC N3 -> TSMC N2: https://www.tsmc.com/english/dedicatedFoundry/technology/platform_smartphone_tech_advancedTech#:~:text=N3E%20is%20an%20optimized%203nm,an%20optical%20shrink%20of%20N3E.
* TSMC N2 -> TSMC A14: https://www.tomshardware.com/tech-industry/tsmc-unveils-1-4nm-technology-2nd-gen-gaa-transistors-full-node-advantages-coming-in-2028
* TSMC A14 -> TSMC A10: No data yet so assume 0.8 scale factor.

From the available sparse scaling data, we compute the densified scale factors between all technology nodes for power projections.
