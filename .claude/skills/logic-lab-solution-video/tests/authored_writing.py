"""Acceptance-only authored row boundaries, inspected on the frozen 1440x810 PDFs."""
from test_writing_units import unit
from solution_video.contracts import InputError
# Explicit row breaks include scripts in the same row. No generic PDF-reading heuristic.
ROW_BREAKS={
 'E10.13':[[275,295],[345,364],[413,432],[487,508],[610,630]],
 'E10.11':[[275,297],[350,374],[425,448,472,493],[628]],
 '2021-1_중간-Q3':[[274,300,325,342],[380,405,426,447,478,503],[274,294],[333,356,381,417,450,478],[610,636]]}

def author_units(layers,problem_id):
    gs={g['id']:g for g in layers['glyphs']};ss={s['id']:s for s in layers['shapes']}
    for si,(step,breaks) in enumerate(zip(layers['map']['steps'],ROW_BREAKS[problem_id])):
        column='right' if problem_id=='2021-1_중간-Q3' and si in (2,3) else 'left'
        bins=[[] for _ in range(len(breaks)+1)]
        for kind,ids,objects in [('glyph',step['glyph_ids'],gs),('shape',step['shape_ids'],ss)]:
            for ident in ids:
                b=objects[ident]['bbox'];center=(b[1]+b[3])/2
                row=sum(center>=edge for edge in breaks);bins[row].append((kind,objects[ident]))
        units=[]
        for ri,targets in enumerate(bins):
            if not targets:continue
            # Bands at original glyph/shape edges; overlap is clipped, not reordered text.
            intervals=sorted((o['bbox'][0],o['bbox'][2]) for kind,o in targets if kind=='glyph' and not o['text'].isspace() or kind=='shape' and o['bbox'][2]-o['bbox'][0]<30)
            merged=[]
            for lo,hi in intervals:
                if merged and lo<merged[-1][1]:merged[-1][1]=max(hi,merged[-1][1])
                else:merged.append([lo,hi])
            left=min(o['bbox'][0] for _,o in targets);right=max(o['bbox'][2] for _,o in targets)
            cuts=sorted(set([left,right]+[(a[1]+b[0])/2 for a,b in zip(merged,merged[1:])]))
            wide_box=any(kind=='shape' and o.get('kind')=='answer_box' and o['bbox'][2]-o['bbox'][0]>600 for kind,o in targets)
            if wide_box:cuts=sorted(set(cuts+[900]))
            if len(cuts)==1:cuts.append(cuts[0]+1)
            for bi,(lo,hi) in enumerate(zip(cuts,cuts[1:])):
                selected={kind:[] for kind in ('glyph','shape')}
                for kind,o in targets:
                    b=o['bbox'];zero=b[2]==b[0] or kind=='glyph' and o['text'].isspace()
                    if (zero and (lo<=b[0]<hi or bi==len(cuts)-2 and b[0]==hi)) or (not zero and b[0]<hi and b[2]>lo):selected[kind].append(o['id'])
                if not selected['glyph'] and not selected['shape']:continue
                # Reviewed semantic chunk boundary for the unusually long E10.11 load explanation.
                chunk=1 if problem_id=='E10.11' and si==1 and ri in (1,2) and lo>=800 else 0
                if wide_box:chunk=1 if lo>=900 else 0
                chunk_id=f'chunk_{si}_{ri}_{chunk}'
                changing=bool(units) and units[-1]['line_id']==f'line_{si}_{ri}' and units[-1]['chunk_id']!=chunk_id
                units.append(unit(f'u_{si}_{ri}_{bi}',[lo,hi],selected['glyph'],selected['shape'],line=f'line_{si}_{ri}',chunk=chunk_id,column=column,camera_break=changing))
        step['writing_units']=units
    from solution_video.writing_units import compile_writing_units
    compile_writing_units(layers)
    return layers
