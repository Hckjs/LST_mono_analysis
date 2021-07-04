OUTDIR = /fefs/aswg/workspace/jonas.hackfeld/build
PLOTS = plots

OBSDIR = /fefs/aswg/workspace/jonas.hackfeld/masterarbeit/obs/crab/20201121/tailcuts_10_5
SIMDIR = /fefs/aswg/workspace/jonas.hackfeld/masterarbeit/mc/ctapipe/merged_all


AICT_CONFIG = config/cta_full_config.yaml


GAMMA_FILE = gamma_trans80_tc_8_4
GAMMA_DIFFUSE_FILE = gamma_diffuse_trans80_tc_8_4
PROTON_FILE = proton_trans80_tc_8_4
ELECTRON_FILE = electron_trans80_tc_8_4


CRAB_RUNS=2988 2989 2990 2991 2992

CRAB_DL2=$(addsuffix .h5, $(addprefix $(OUTDIR)/dl2_dvr_tc_10_5_LST-1.Run0, $(CRAB_RUNS)))
CRAB_DL2_DVR=$(addsuffix .h5, $(addprefix $(OUTDIR)/dl2_dvr_tc_10_5_ped_LST-1.Run0, $(CRAB_RUNS)))


all: $(OUTDIR)/cv_separation.h5 \
	$(OUTDIR)/cv_disp.h5 \
	$(OUTDIR)/cv_regressor.h5 \
	$(PLOTS)/regressor_plots.pdf \
	$(PLOTS)/disp_plots.pdf \
	$(PLOTS)/separator_plots.pdf \
	$(CRAB_DL2_DVR) \
	$(CRAB_DL2) \
	$(OUTDIR)/dl2_$(GAMMA_FILE)_testing.h5 \
	$(OUTDIR)/dl2_$(GAMMA_DIFFUSE_FILE)_testing.h5 \
	$(OUTDIR)/dl2_$(PROTON_FILE)_testing.h5 \
	$(OUTDIR)/dl2_$(ELECTRON_FILE)_testing.h5 \
	$(OUTDIR)/pyirf.fits.gz \
	$(PLOTS)/crab_theta2.pdf \
	$(PLOTS)/crab_theta2_dvr.pdf

#precuts
$(OUTDIR)/%_precuts.h5: $(SIMDIR)/%.h5 $(AICT_CONFIG) | $(OUTDIR)
	aict_apply_cuts \
		$(AICT_CONFIG) \
		$< \
		$@

#train models
$(OUTDIR)/separator.pkl $(OUTDIR)/cv_separation.h5: $(AICT_CONFIG) $(OUTDIR)/dl1_$(PROTON_FILE)_training_precuts.h5 | $(OUTDIR)
$(OUTDIR)/separator.pkl $(OUTDIR)/cv_separation.h5: $(OUTDIR)/dl1_$(GAMMA_DIFFUSE_FILE)_training_precuts.h5 | $(OUTDIR)
	aict_train_separation_model \
		$(AICT_CONFIG) \
		$(OUTDIR)/dl1_$(GAMMA_DIFFUSE_FILE)_training_precuts.h5 \
		$(OUTDIR)/dl1_$(PROTON_FILE)_training_precuts.h5 \
		$(OUTDIR)/cv_separation.h5 \
		$(OUTDIR)/separator.pkl

$(OUTDIR)/disp.pkl $(OUTDIR)/sign.pkl $(OUTDIR)/cv_disp.h5: $(AICT_CONFIG) $(OUTDIR)/dl1_$(GAMMA_DIFFUSE_FILE)_training_precuts.h5 | $(OUTDIR)
	aict_train_disp_regressor \
		$(AICT_CONFIG) \
		$(OUTDIR)/dl1_$(GAMMA_DIFFUSE_FILE)_training_precuts.h5 \
		$(OUTDIR)/cv_disp.h5 \
		$(OUTDIR)/disp.pkl \
		$(OUTDIR)/sign.pkl

$(OUTDIR)/regressor.pkl $(OUTDIR)/cv_regressor.h5: $(AICT_CONFIG) $(OUTDIR)/dl1_$(GAMMA_FILE)_training_precuts.h5 | $(OUTDIR)
	aict_train_energy_regressor \
		$(AICT_CONFIG) \
		$(OUTDIR)/dl1_$(GAMMA_FILE)_training_precuts.h5 \
		$(OUTDIR)/cv_regressor.h5 \
		$(OUTDIR)/regressor.pkl

#apply models
$(OUTDIR)/dl2_%.h5: $(OBSDIR)/dl1_%.h5 $(OUTDIR)/separator.pkl $(OUTDIR)/disp.pkl $(OUTDIR)/regressor.pkl $(AICT_CONFIG) | $(OUTDIR)
	aict_apply_cuts \
		$(AICT_CONFIG) \
		$< \
		$@ \
		--chunksize=500000

	aict_apply_separation_model \
		$(AICT_CONFIG) \
		$@ \
		$(OUTDIR)/separator.pkl \
		--chunksize=500000

	aict_apply_disp_regressor \
		$(AICT_CONFIG) \
		$@ \
		$(OUTDIR)/disp.pkl \
		$(OUTDIR)/sign.pkl \
		--chunksize=500000

	aict_apply_energy_regressor \
		$(AICT_CONFIG) \
		$@ \
		$(OUTDIR)/regressor.pkl \
		--chunksize=500000

#apply models
$(OUTDIR)/dl2_%_testing.h5: $(SIMDIR)/dl1_%_testing.h5 $(OUTDIR)/separator.pkl $(OUTDIR)/disp.pkl $(OUTDIR)/regressor.pkl $(AICT_CONFIG) | $(OUTDIR)
	aict_apply_cuts \
		$(AICT_CONFIG) \
		$< \
		$@ \
		--chunksize=500000

	aict_apply_separation_model \
		$(AICT_CONFIG) \
		$@ \
		$(OUTDIR)/separator.pkl \
		--chunksize=500000

	aict_apply_disp_regressor \
		$(AICT_CONFIG) \
		$@ \
		$(OUTDIR)/disp.pkl \
		$(OUTDIR)/sign.pkl \
		--chunksize=500000

	aict_apply_energy_regressor \
		$(AICT_CONFIG) \
		$@ \
		$(OUTDIR)/regressor.pkl \
		--chunksize=500000


#performance plots
$(PLOTS)/regressor_plots.pdf: $(AICT_CONFIG) $(OUTDIR)/cv_regressor.h5 | $(OUTDIR)
	aict_plot_regressor_performance \
		$(AICT_CONFIG) \
		$(OUTDIR)/cv_regressor.h5 \
		$(OUTDIR)/regressor.pkl \
		-o $@

$(PLOTS)/separator_plots.pdf: $(AICT_CONFIG) $(OUTDIR)/cv_separation.h5 | $(OUTDIR)
	aict_plot_separator_performance \
		$(AICT_CONFIG) \
		$(OUTDIR)/cv_separation.h5 \
		$(OUTDIR)/separator.pkl \
		-o $@

$(PLOTS)/disp_plots.pdf: $(AICT_CONFIG) $(OUTDIR)/cv_disp.h5 $(OUTDIR)/dl1_$(GAMMA_DIFFUSE_FILE)_training_precuts.h5 | $(OUTDIR)
	aict_plot_disp_performance \
		$(AICT_CONFIG) \
		$(OUTDIR)/cv_disp.h5 \
		$(OUTDIR)/dl1_$(GAMMA_DIFFUSE_FILE)_training_precuts.h5 \
		$(OUTDIR)/disp.pkl \
		$(OUTDIR)/sign.pkl \
		-o $@

#observations
$(PLOTS)/crab_theta2.pdf: theta2_wobble.py plotting.py calculation.py $(OUTDIR)/pyirf.fits.gz $(CRAB_DL2) | $(OUTDIR)
	python theta2_wobble.py \
		$@ \
		$(CRAB_DL2) \
		'Crab' \
		$(OUTDIR)/pyirf.fits.gz \
		0.04 \
		0.80

$(PLOTS)/crab_theta2_dvr.pdf: theta2_wobble.py plotting.py calculation.py $(OUTDIR)/pyirf.fits.gz $(CRAB_DL2_DVR) | $(OUTDIR)
	python theta2_wobble.py \
		$@ \
		$(CRAB_DL2_DVR) \
		'Crab' \
		$(OUTDIR)/pyirf.fits.gz \
		0.04 \
		0.80

#pyirf sensitivity 
$(OUTDIR)/pyirf.fits.gz: pyirf_sensitivity.py $(OUTDIR)/dl2_$(GAMMA_FILE)_testing.h5 $(OUTDIR)/dl2_$(PROTON_FILE)_testing.h5 $(OUTDIR)/dl2_$(ELECTRON_FILE)_testing.h5 | $(OUTDIR)
	python pyirf_sensitivity.py \
		$(OUTDIR)/dl2_$(GAMMA_FILE)_testing.h5 \
		$(OUTDIR)/dl2_$(PROTON_FILE)_testing.h5 \
		$(OUTDIR)/dl2_$(ELECTRON_FILE)_testing.h5 \
		$(OUTDIR)/pyirf.fits.gz


$(OUTDIR):
	mkdir -p $(OUTDIR)

clean:
	rm -rf $(OUTDIR)


.PHONY: all clean
