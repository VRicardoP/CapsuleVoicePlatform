import React, { useState } from 'react';
import type { WACatalogItem } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';
import { usePaginatedFetch } from '../../../hooks/usePaginatedFetch';
import { useModalState } from '../../../hooks/useModalState';

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  active: { label: 'Activo', color: 'bg-green-600' },
  inactive: { label: 'Inactivo', color: 'bg-gray-600' },
  out_of_stock: { label: 'Sin stock', color: 'bg-red-600' },
};

const CatalogPage: React.FC = () => {
  const { toast } = useToast();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [form, setForm] = useState({ name: '', description: '', price: '', currency: 'EUR', image_url: '', product_url: '', category: '', sku: '', stock: '' });

  const { items, total, loading, page, setPage, totalPages, refetch } = usePaginatedFetch<WACatalogItem>(
    (skip, limit, filters) => whatsappApi.getCatalogItems({ search: filters.search, status: filters.status, skip, limit }),
    { pageSize: 12, filters: { search: search || undefined, status: statusFilter || undefined } },
  );

  const { showModal, editId, deleteId, openCreate, openEdit, closeModal, confirmDelete, cancelDelete } = useModalState();

  const resetForm = () => { setForm({ name: '', description: '', price: '', currency: 'EUR', image_url: '', product_url: '', category: '', sku: '', stock: '' }); };

  const handleSave = async () => {
    if (!form.name || !form.price) return;
    try {
      const data = {
        name: form.name, description: form.description || undefined, price: parseFloat(form.price),
        image_url: form.image_url || undefined, product_url: form.product_url || undefined,
        category: form.category || undefined,
        sku: form.sku || undefined, stock: form.stock ? parseInt(form.stock) : undefined,
      };
      if (editId) { await whatsappApi.updateCatalogItem(editId, data); toast('Producto actualizado'); }
      else { await whatsappApi.createCatalogItem({ ...data, currency: form.currency }); toast('Producto creado'); }
      closeModal(); resetForm(); refetch();
    } catch { toast('Error guardando producto', 'error'); }
  };

  const handleEdit = (item: WACatalogItem) => {
    setForm({ name: item.name, description: item.description || '', price: String(item.price), currency: item.currency,
      image_url: item.image_url || '', product_url: item.product_url || '', category: item.category || '', sku: item.sku || '', stock: item.stock != null ? String(item.stock) : '' });
    openEdit(item.id);
  };

  const handleToggleStatus = async (item: WACatalogItem) => {
    try {
      const ns = item.status === 'active' ? 'inactive' : 'active';
      await whatsappApi.updateCatalogItem(item.id, { status: ns });
      toast(ns === 'active' ? 'Producto activado' : 'Producto desactivado'); refetch();
    } catch { toast('Error cambiando estado', 'error'); }
  };

  const handleDeleteConfirmed = async () => {
    if (!deleteId) return;
    try { await whatsappApi.deleteCatalogItem(deleteId); toast('Producto eliminado'); refetch(); }
    catch { toast('Error eliminando', 'error'); }
    cancelDelete();
  };

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div>
        <div className="flex items-center justify-between mb-1">
          <h1 className="text-2xl font-bold text-white">Catalogo de Productos</h1>
          <button onClick={() => { resetForm(); openCreate(); }} className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg font-medium transition">+ Nuevo producto</button>
        </div>
        <p className="text-gray-400 text-sm">Gestiona los productos de tu catalogo de WhatsApp</p>
      </div>

      <div className="flex-1 min-h-64 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex flex-col">
        <div className="px-4 py-3 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar productos..."
              className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white placeholder-gray-500 w-64 focus:outline-none focus:border-green-500" />
            <div className="flex gap-2">
              {['', 'active', 'inactive', 'out_of_stock'].map(s => (
                <button key={s} onClick={() => setStatusFilter(s)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium ${statusFilter === s ? 'bg-green-600/20 text-green-400 border border-green-500/30' : 'border border-gray-600 text-gray-400'}`}>
                  {s ? (STATUS_LABELS[s]?.label || s) : 'Todos'}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-32"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" /></div>
          ) : items.length === 0 ? (
            <div className="flex items-center justify-center h-32">
              <div className="bg-gray-900/50 border border-dashed border-gray-700 rounded-xl px-8 py-6 text-center">
                <p className="text-gray-500 text-sm">No hay productos en el catalogo</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-4">
              {items.map(item => {
                const st = STATUS_LABELS[item.status] || { label: item.status, color: 'bg-gray-600' };
                return (
                  <div key={item.id} className="bg-gray-900/50 rounded-xl border border-gray-700 overflow-hidden hover:border-green-500/30 transition group">
                    {item.image_url ? (
                      <div className="h-36 bg-gray-700 overflow-hidden"><img src={item.image_url} alt={item.name} className="w-full h-full object-cover" /></div>
                    ) : (
                      <div className="h-36 bg-gray-700 flex items-center justify-center"><span className="text-3xl text-gray-600">&#128230;</span></div>
                    )}
                    <div className="p-4">
                      <div className="flex items-start justify-between mb-1">
                        <h3 className="text-sm font-medium text-white truncate">{item.name}</h3>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] text-white flex-shrink-0 ml-2 ${st.color}`}>{st.label}</span>
                      </div>
                      {item.category && <p className="text-[10px] text-gray-500 mb-1">{item.category}</p>}
                      {item.description && <p className="text-xs text-gray-400 line-clamp-2 mb-2">{item.description}</p>}
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-lg font-bold text-green-400">{Number(item.price).toLocaleString('es-ES', { minimumFractionDigits: 2 })} {item.currency}</span>
                        {item.stock != null && <span className={`text-[10px] ${item.stock > 0 ? 'text-gray-500' : 'text-red-400'}`}>Stock: {item.stock}</span>}
                      </div>
                      {item.sku && <p className="text-[10px] text-gray-600 mb-2">SKU: {item.sku}</p>}
                      <div className="flex items-center gap-2 text-xs">
                        <button onClick={() => handleEdit(item)} className="text-blue-400 hover:text-blue-300">Editar</button>
                        <button onClick={() => handleToggleStatus(item)}
                          className={item.status === 'active' ? 'text-orange-400 hover:text-orange-300' : 'text-green-400 hover:text-green-300'}>
                          {item.status === 'active' ? 'Desactivar' : 'Activar'}
                        </button>
                        <button onClick={() => confirmDelete(item.id)} className="text-gray-600 hover:text-red-400 ml-auto">Eliminar</button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-gray-700 flex items-center justify-between text-sm text-gray-400">
            <span>{total} productos</span>
            <div className="flex gap-2">
              <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-700 hover:border-gray-600 transition disabled:opacity-50">Anterior</button>
              <span className="px-3 py-1.5">{page + 1} / {totalPages}</span>
              <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)} className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-700 hover:border-gray-600 transition disabled:opacity-50">Siguiente</button>
            </div>
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={e => e.target === e.currentTarget && (() => { closeModal(); resetForm(); })()}>
          <div className="bg-gray-800 rounded-2xl p-6 w-[500px] border border-gray-700 max-h-[80vh] overflow-auto">
            <h2 className="text-white font-bold mb-4">{editId ? 'Editar' : 'Nuevo'} producto</h2>
            <div className="space-y-3">
              <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Nombre del producto"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
              <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="Descripcion (opcional)"
                rows={3} className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-green-500" />
              <div className="flex gap-2">
                <input type="number" value={form.price} onChange={e => setForm({ ...form, price: e.target.value })} placeholder="Precio"
                  className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
                <select value={form.currency} onChange={e => setForm({ ...form, currency: e.target.value })}
                  className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white w-24 focus:outline-none focus:border-green-500">
                  <option value="EUR">EUR</option><option value="USD">USD</option><option value="GBP">GBP</option>
                </select>
              </div>
              <input type="text" value={form.image_url} onChange={e => setForm({ ...form, image_url: e.target.value })} placeholder="URL de imagen (opcional)"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
              <input type="text" value={form.product_url} onChange={e => setForm({ ...form, product_url: e.target.value })} placeholder="URL del producto (para botón en template)"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
              <div className="flex gap-2">
                <input type="text" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} placeholder="Categoria"
                  className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
                <input type="text" value={form.sku} onChange={e => setForm({ ...form, sku: e.target.value })} placeholder="SKU"
                  className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
              </div>
              <input type="number" value={form.stock} onChange={e => setForm({ ...form, stock: e.target.value })} placeholder="Stock disponible (opcional)"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500" />
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => { closeModal(); resetForm(); }} className="px-4 py-2 text-sm text-gray-400 hover:text-white font-medium transition">Cancelar</button>
              <button onClick={handleSave} className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 font-medium transition">{editId ? 'Guardar' : 'Crear'}</button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog open={!!deleteId} title="Eliminar producto"
        message="¿Seguro que quieres eliminar este producto del catalogo?" confirmLabel="Eliminar"
        onConfirm={handleDeleteConfirmed} onCancel={cancelDelete} />
    </div>
  );
};

export default CatalogPage;
