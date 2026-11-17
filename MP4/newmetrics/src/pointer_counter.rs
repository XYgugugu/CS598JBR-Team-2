use rustc_hir::{self, intravisit};
use rustc_middle::ty::{TyCtxt, TypeckResults};
use rustc_middle::hir::nested_filter;
use rustc_span::Span;

use crate::utils::*;

macro_rules! skip_generated_code {
    ($span: expr) => {
        if $span.from_expansion() || $span.is_dummy() {
            return;
        }
    };
}

pub struct PointerCounter<'tcx> {
    tcx: TyCtxt<'tcx>,
    current_typeck: Option<&'tcx TypeckResults<'tcx>>,
    pub all_derefs: Vec<Span>,
    pub all_decls: Vec<Span>,
    pub selected_fns: Vec<String>,
}

impl<'tcx> PointerCounter<'tcx> {
    pub fn new(tcx: &TyCtxt<'tcx>, selected_fns: Vec<String>) -> PointerCounter<'tcx> {
        PointerCounter{
            tcx: *tcx,
            current_typeck: None,
            all_derefs: Vec::new(),
            all_decls: Vec::new(),
            selected_fns,
        }
    }
}

impl<'tcx> intravisit::Visitor<'tcx> for PointerCounter<'tcx> {

    type NestedFilter = nested_filter::OnlyBodies;

    fn maybe_tcx(&mut self) -> Self::MaybeTyCtxt {
        self.tcx
    }


    fn visit_item(&mut self, item: &'tcx rustc_hir::Item) {
        let fname = self.tcx.sess.source_map().span_to_diagnostic_string(item.span.clone());
        if fname.starts_with('/'){
            return;
        }
        // skip_generated_code!(item.span);
        match &item.kind {
            rustc_hir::ItemKind::Impl(impl_data) => {
                for impl_item_ref in impl_data.items {
                    let impl_item = self.tcx.hir_impl_item(impl_item_ref.id);
                }
                let old_typeck = self.current_typeck;
                if self.tcx.has_typeck_results(item.owner_id.def_id) {
                    self.current_typeck = Some(self.tcx.typeck(item.owner_id.def_id));
                }
                else {
                    self.current_typeck = None;
                }
                intravisit::walk_item(self, item);
                self.current_typeck = old_typeck;            },
            _ => {
                let old_typeck = self.current_typeck;
                if self.tcx.has_typeck_results(item.owner_id.def_id) {
                    self.current_typeck = Some(self.tcx.typeck(item.owner_id.def_id));
                }
                else {
                    self.current_typeck = None;
                }
                intravisit::walk_item(self, item);
                self.current_typeck = old_typeck;
            }
        }
    }

    fn visit_expr(&mut self, expr: &'tcx rustc_hir::Expr) {
        let fname = self.tcx.sess.source_map().span_to_diagnostic_string(expr.span.clone());
        if fname.starts_with('/'){
            return;
        }
        // skip_generated_code!(expr.span);
        if let rustc_hir::ExprKind::Unary(rustc_hir::UnOp::Deref, sub_expr) = expr.kind {
            if let Some(typeck) = self.current_typeck {
                if typeck.expr_ty(sub_expr).is_raw_ptr() {
                    self.all_derefs.push(expr.span);
                }
            }
        }
        intravisit::walk_expr(self, expr);
    }
    fn visit_pat(&mut self, pat: &'tcx rustc_hir::Pat) {
        let fname = self.tcx.sess.source_map().span_to_diagnostic_string(pat.span.clone());
        if fname.starts_with('/'){
            return;
        }
        // skip_generated_code!(pat.span);
        pat.walk_always(|p| {
            if let rustc_hir::PatKind::Binding(_, _, _, _) = p.kind {
                if let Some(typeck) = self.current_typeck {
                    let ty = typeck.pat_ty(pat);
                    if ty.is_raw_ptr() {
                        self.all_decls.push(pat.span);
                    }
                }
            }
        });
        intravisit::walk_pat(self, pat);
    }
}
