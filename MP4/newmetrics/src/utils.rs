use rustc_hir::{HirId, Node, ConstContext};
use rustc_hir::def_id::DefId;
use rustc_span::{Span, FileNameDisplayPreference, Pos};
use rustc_middle::ty::TyCtxt;
use rustc_middle::mir::{Local, Body, BasicBlock, BasicBlockData, Statement, StatementKind, VarDebugInfoContents};

use rustc_span::source_map::SourceMap;
use rustc_span::{SpanSnippetError, BytePos};

pub fn span_to_string<'tcx>(tcx: TyCtxt<'tcx>, span: &Span) -> String {
    let source_map = tcx.sess.source_map();
    source_map.span_to_snippet(span.clone()).unwrap()
}

pub fn span_to_diagnostic<'tcx>(tcx: TyCtxt<'tcx>, span: &Span) -> String {
    let source_map = tcx.sess.source_map();
    source_map.span_to_diagnostic_string(span.clone())
}

pub fn span_to_data<'tcx>(tcx: TyCtxt<'tcx>, span: &Span) -> ((String, usize, usize), (String, usize, usize)){
    let source_map = tcx.sess.source_map();
    let low_pos = source_map.lookup_char_pos(span.lo());
    let high_pos = source_map.lookup_char_pos(span.hi());
    let low_fname = low_pos.file.name.display(FileNameDisplayPreference::Remapped).to_string();
    let high_fname = high_pos.file.name.display(FileNameDisplayPreference::Remapped).to_string();

    ((low_fname, low_pos.line, low_pos.col.to_usize() + 1),
     (high_fname, high_pos.line, high_pos.col.to_usize() + 1))
}

pub fn get_span_lines<'tcx>(tcx: TyCtxt<'tcx>, span: &Span) -> usize {
    let ((_, start_line, _), (_, end_line, _)) = span_to_data(tcx, span);
    end_line - start_line + 1
}
