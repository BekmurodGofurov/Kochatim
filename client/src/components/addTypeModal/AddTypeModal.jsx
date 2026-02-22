import React, { useState } from "react";
import { X } from "lucide-react";
import { apiFetch } from "../../api/https";
import "./AddTypeModal.scss";

export default function AddTypeModal({ cId, onClose, onSuccess }) {
    const [typeName, setTypeName] = useState("");
    const [description, setDescription] = useState("");
    const [image, setImage] = useState(null);
    const [imagePreview, setImagePreview] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            setImage(file);
            const reader = new FileReader();
            reader.onloadend = () => {
                setImagePreview(reader.result);
            };
            reader.readAsDataURL(file);
        }
    };

    const uploadToImgBB = async (file) => {
        const apiKey = import.meta.env.VITE_IMGBB_API_KEY || "YOUR_IMGBB_API_KEY";
        const formData = new FormData();
        formData.append("image", file);

        const response = await fetch(`https://api.imgbb.com/1/upload?key=${apiKey}`, {
            method: "POST",
            body: formData,
        });

        const data = await response.json();
        if (data.success) {
            return data.data.url;
        } else {
            throw new Error("Rasm yuklashda xatolik yuz berdi");
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!typeName.trim() || !description.trim() || !image || isSubmitting) return;

        setIsSubmitting(true);
        try {
            // 1. Upload image
            const imageUrl = await uploadToImgBB(image);

            // 2. Save type
            await apiFetch("/api/types/me", {
                method: "POST",
                body: {
                    c_id: cId,
                    t_name: typeName.trim(),
                    deff: description.trim(),
                    image_url: imageUrl
                }
            });
            onSuccess?.();
        } catch (err) {
            alert(err.message || "Nav qo'shishda xatolik yuz berdi");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="inv-modal inv-modal--add" role="dialog" aria-modal="true">
            <div className="inv-modal__panel inv-modal__panel--small">
                <div className="inv-modal__top">
                    <h2 className="inv-modal__title">Yangi Nav</h2>
                    <button
                        type="button"
                        className="inv-modal__close"
                        onClick={onClose}
                    >
                        <X size={26} />
                    </button>
                </div>
                <div className="inv-modal__accent" />

                <form onSubmit={handleSubmit} className="inv-modal__form">
                    <div className="inv-modal__block">
                        <div className="inv-modal__kicker">Rasm yuklang (Majburiy)</div>
                        <div className="inv-image-upload">
                            <label className="inv-image-upload__dropzone">
                                <input
                                    type="file"
                                    className="inv-image-upload__input"
                                    accept="image/*"
                                    onChange={handleFileChange}
                                    required
                                />
                                {imagePreview ? (
                                    <img src={imagePreview} alt="Preview" className="inv-image-upload__preview" />
                                ) : (
                                    <div className="inv-image-upload__placeholder">
                                        <span>Rasm tanlash uchun bosing</span>
                                    </div>
                                )}
                            </label>
                        </div>
                    </div>

                    <div className="inv-modal__block">
                        <div className="inv-modal__kicker">Nav nomi</div>
                        <input
                            type="text"
                            className="inv-form-input"
                            placeholder="Masalan: Qizil Olma, Golden..."
                            value={typeName}
                            onChange={(e) => setTypeName(e.target.value)}
                            autoFocus
                            required
                        />
                    </div>

                    <div className="inv-modal__block">
                        <div className="inv-modal__kicker">Tavsif (Majburiy)</div>
                        <textarea
                            className="inv-form-input inv-form-input--area"
                            placeholder="Nav haqida qo'shimcha ma'lumot..."
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            rows={3}
                            required
                        />
                    </div>

                    <div className="inv-modal__footer">
                        <button
                            type="submit"
                            className="inv-btn inv-btn--primary inv-btn--full"
                            disabled={isSubmitting || !typeName.trim() || !description.trim() || !image}
                        >
                            {isSubmitting ? "Saqlanmoqda..." : "Yaratish"}
                        </button>
                    </div>
                </form>
            </div>
            <button
                type="button"
                className="inv-modal__backdrop"
                onClick={onClose}
            />
        </div>
    );
}
