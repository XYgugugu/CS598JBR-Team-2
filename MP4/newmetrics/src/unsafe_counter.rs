use rustc_hir::{self, intravisit, Block};
use rustc_middle::ty::TyCtxt;
use rustc_middle::hir::nested_filter;
use rustc_span::Span;

macro_rules! skip_generated_code {
    ($span: expr) => {
        if $span.from_expansion() || $span.is_dummy() {
            return;
        }
    };
}

pub struct UnsafeCounter<'tcx> {
    pub tcx: TyCtxt<'tcx>,
    pub unsafe_spans: Vec<Span>,
    pub unsafe_calls: Vec<Span>,
    pub unsafe_casts: Vec<Span>,
    pub inside_unsafe: bool,
    pub selected_fns: Vec<String>,
}

impl<'tcx> UnsafeCounter<'tcx> {
    pub fn new(tcx: &TyCtxt<'tcx>, selected_fns: Vec<String>) -> UnsafeCounter<'tcx> {
        UnsafeCounter{
            tcx: *tcx,
            unsafe_spans: Vec::new(),
            unsafe_calls: Vec::new(),
            unsafe_casts: Vec::new(),
            inside_unsafe: false,
            selected_fns,
        }
    }
}

impl<'tcx> intravisit::Visitor<'tcx> for UnsafeCounter<'tcx> {

    type NestedFilter = nested_filter::OnlyBodies;

    fn maybe_tcx(&mut self) -> Self::MaybeTyCtxt {
        self.tcx
    }

    fn visit_item(&mut self, item: &'tcx rustc_hir::Item) {
        let fname = self.tcx.sess.source_map().span_to_diagnostic_string(item.span.clone());
        if fname.starts_with('/'){
            return;
        }

        match &item.kind {
            rustc_hir::ItemKind::Fn { sig, generics, body, .. } => {
                let fn_name = item.kind.ident().unwrap().name.as_str().to_string();
                if sig.header.is_unsafe() {
                    // Add the entire function to the list of unsafe spans
                    self.unsafe_spans.push(item.span);

                    let old_inside_unsafe = self.inside_unsafe;
                    self.inside_unsafe = true;
                    self.inside_unsafe = old_inside_unsafe;
                }
                else {
                }
                intravisit::walk_item(self, item);
            },
            rustc_hir::ItemKind::Impl(impl_data) => {
                // println!("impl");
                let self_ty = self.tcx.type_of(impl_data.self_ty.hir_id.owner);

                let mut self_ty_name = "UnknownSelf".to_string();
                let trait_name = if let Some(trait_ref) = impl_data.of_trait {
                    // For `impl Trait for Type`
                    format!(" impl {}", self.tcx.sess.source_map().span_to_snippet(trait_ref.path.span).unwrap_or_else(|_|"UnknownTrait".to_string()))
                } else {
                    // For `impl Type`
                    "".to_string()
                };
                for impl_item_ref in impl_data.items {
                    let impl_item = self.tcx.hir_impl_item(impl_item_ref.id);
                    if let rustc_hir::ImplItemKind::Fn(fn_sig, _body_id) = &impl_item.kind {
                        if fn_sig.header.is_unsafe() {
                            // Add the entire function to the list of unsafe spans
                            self.unsafe_spans.push(impl_item.span);
                        }
                        else {
                        }
                    }
                }
                intravisit::walk_item(self, item);
            },
            _ => {
                // Visit the item
                intravisit::walk_item(self, item);
            }
        }
    }
    fn visit_block(&mut self, block: &'tcx Block) {
        let fname = self.tcx.sess.source_map().span_to_diagnostic_string(block.span.clone());
        if fname.starts_with('/'){
            return;
        }
        // skip_generated_code!(block.span);
        if block.rules == rustc_hir::BlockCheckMode::UnsafeBlock(rustc_hir::UnsafeSource::UserProvided) {
            // Add the entire block to the list of unsafe spans
            self.unsafe_spans.push(block.span);

            let old_inside_unsafe = self.inside_unsafe;
            self.inside_unsafe = true;
            intravisit::walk_block(self, block);
            self.inside_unsafe = old_inside_unsafe;
        }
        else {
            // Visit the block
            intravisit::walk_block(self, block);
        }
    }
    fn visit_expr(&mut self, expr: &'tcx rustc_hir::Expr) {
        let fname = self.tcx.sess.source_map().span_to_diagnostic_string(expr.span.clone());
        if fname.starts_with('/'){
            return;
        }
        // skip_generated_code!(expr.span);
        if self.inside_unsafe {
            match &expr.kind {
                rustc_hir::ExprKind::Call(..) =>  {
                    // Add the call to the list of unsafe calls
                    self.unsafe_calls.push(expr.span);
                },
                rustc_hir::ExprKind::MethodCall(..) => {
                    // Add the call to the list of unsafe calls
                    self.unsafe_calls.push(expr.span);
                },
                rustc_hir::ExprKind::Cast(..) => {
                    // Add the cast to the list of unsafe casts
                    self.unsafe_casts.push(expr.span);
                },
                _ => {}
            }
        }
        intravisit::walk_expr(self, expr);
    }
}
